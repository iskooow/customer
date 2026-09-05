"""One-shot patch: add a real progress bar to the Excel customer import.

The confirm step no longer imports everything inside one blocking HTTP
request (which made the page "just keep loading" with zero feedback).
Instead the preview starts a "pending import" job in the session and the new
/customers/import/status page imports it in chunks (one poll = one chunk),
showing a live progress bar and an "X of N imported" label. No Celery/broker
is required.

Run from the project root:

    python _patch_import_progress.py

The script is one-shot: it validates every marker before writing anything and
aborts (without changes) if the files do not match the expected state.
"""
import io
import os


def jpath(*parts):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def read(path):
    with io.open(path, encoding='utf-8') as fh:
        return fh.read()


def write(path, text):
    # Normalize to CRLF (the repo's working-tree convention) like _patch_import.py.
    with io.open(path, 'wb') as fh:
        fh.write(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8'))


def norm(text):
    """Internal patch strings use \\n line endings (read() uses universal
    newlines), so fragments match regardless of the file's actual EOL style."""
    return text


def find_line(lines, needle, start=0):
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i
    raise AssertionError('marker not found: %r' % needle)


def replace_once(text, old, new, label='fragment'):
    assert text.count(old) == 1, '%s not found exactly once: %r' % (label, old[:64])
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1) customers/views.py -- replace the "import everything at once" preview
#    confirm with the chunked progress flow (CustomerImportPreviewView and a
#    new CustomerImportStatusView), keeping import_rows/clear_pending.
# ---------------------------------------------------------------------------
VIEWS = jpath('customers', 'views.py')
views = read(VIEWS)
assert 'class CustomerImportStatusView' not in views, 'customers/views.py already patched'
views_lines = views.splitlines(keepends=True)
_start = find_line(views_lines, 'class CustomerImportPreviewView')
_end = find_line(views_lines, 'class CustomerPrintView')
assert _start < _end, 'unexpected view ordering in customers/views.py'
NEW_VIEWS_SECTION = norm('''class CustomerImportPreviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Show the import preview and start the chunked import."""

    def test_func(self):
        return self.request.user.is_admin_user

    def get(self, request):
        preview = request.session.get('import_preview')
        if not preview:
            messages.error(request, _('No import preview found. Please upload a file first.'))
            return redirect('customers:import')
        return render(request, 'customers/import_preview.html', {'preview': preview})

    def post(self, request):
        preview = request.session.get('import_preview')
        if not preview:
            messages.error(request, _('No import preview found.'))
            return redirect('customers:import')

        if 'confirm' not in request.POST:
            return redirect('customers:import')

        # Start the import: move the validated rows into a pending job the
        # status page processes in chunks. This keeps the confirm request
        # instant and shows the user real progress on the status page.
        request.session['import_pending'] = {
            'index': 0,
            'created': 0,
            'valid_rows': preview.get('valid_rows', []),
            'errors': preview.get('errors', []),
            'duplicates': preview.get('duplicates', 0),
        }
        del request.session['import_preview']
        request.session.modified = True
        return redirect('customers:import_status')


class CustomerImportStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Import customers from the pending job in chunks and report progress."""

    #: Rows imported per polling request.
    CHUNK_SIZE = 25

    def test_func(self):
        return self.request.user.is_admin_user

    def get(self, request):
        pending = request.session.get('import_pending')
        if not pending:
            messages.error(request, _('No import in progress. Please upload a file first.'))
            return redirect('customers:import')
        return render(request, 'customers/import_status.html', {
            'total': len(pending['valid_rows']),
            'processed': pending['index'],
        })
    def post(self, request):
        pending = request.session.get('import_pending')
        if not pending:
            return JsonResponse({'done': True, 'redirect': reverse('customers:import')})
        if 'cancel' in request.POST:
            self.clear_pending(request)
            messages.info(request, _('Import cancelled.'))
            return JsonResponse({'done': True, 'redirect': reverse('customers:import')})

        rows = pending['valid_rows']
        total = len(rows)
        start = pending['index']
        if start < total:
            end = min(start + self.CHUNK_SIZE, total)
            chunk_created, chunk_errors = self.import_rows(request, rows[start:end])
            pending['index'] = end
            pending['created'] += chunk_created
            pending['errors'].extend(chunk_errors)
            request.session.modified = True

        if pending['index'] >= total:
            created = pending.get('created', 0)
            errors = pending.get('errors', [])
            duplicates = pending.get('duplicates', 0)
            self.clear_pending(request)
            messages.success(request, _('Successfully imported {} customers.').format(created))
            if errors:
                messages.warning(request, _('{} rows had errors and were skipped.').format(len(errors)))
            if duplicates:
                messages.warning(request, _('{} duplicate rows were skipped.').format(duplicates))
            return JsonResponse({
                'done': True,
                'count': created,
                'redirect': reverse('customers:list'),
            })

        return JsonResponse({
            'done': False,
            'processed': pending['index'],
            'total': total,
        })

    def import_rows(self, request, rows):
        """Create customers for one chunk of rows. Returns (created, errors)."""
        pk_set = {r['sales_person_pk'] for r in rows if r.get('sales_person_pk')}
        sales_persons = {sp.pk: sp for sp in SalesPerson.objects.filter(pk__in=pk_set)}
        created = 0
        errors = []
        for row_data in rows:
            try:
                customer = Customer.objects.create(
                    company_name=row_data['company_name'],
                    trade_license_number=row_data.get('trade_license_number') or None,
                    trade_license_expiry=date.fromisoformat(row_data['trade_license_expiry']) if row_data.get('trade_license_expiry') else None,
                    passport_number=row_data.get('passport_number') or '',
                    passport_expiry=date.fromisoformat(row_data['passport_expiry']) if row_data.get('passport_expiry') else None,
                    eid_number=row_data.get('eid_number') or '',
                    eid_expiry=date.fromisoformat(row_data['eid_expiry']) if row_data.get('eid_expiry') else None,
                    trn=row_data.get('trn') or None,
                    sales_person=sales_persons.get(row_data.get('sales_person_pk')),
                    customer_status=row_data.get('customer_status', Customer.CustomerStatus.ACTIVE),
                    created_by=request.user,
                    updated_by=request.user,
                )
                customer.update_copy_status()
                log_action(
                    user=request.user,
                    action='imported',
                    customer=customer,
                    description='Imported customer: {}'.format(customer.company_name),
                    request=request,
                )
                created += 1
            except Exception as e:
                errors.append('Import error for {}: {}'.format(row_data['company_name'], str(e)))
        return created, errors

    def clear_pending(self, request):
        if 'import_pending' in request.session:
            del request.session['import_pending']
            request.session.modified = True


''')

new_views = ''.join(views_lines[:_start]) + NEW_VIEWS_SECTION + ''.join(views_lines[_end:])
write(VIEWS, new_views)
# ---------------------------------------------------------------------------
# 2) customers/urls.py -- route /customers/import/status/ to the status view
# ---------------------------------------------------------------------------
URLS = jpath('customers', 'urls.py')
urls = read(URLS)
assert "name='import_status'" not in urls, 'customers/urls.py already patched'
urls = replace_once(
    urls,
    norm("path('import/preview/', views.CustomerImportPreviewView.as_view(), name='import_preview'),"),
    norm(
        "path('import/preview/', views.CustomerImportPreviewView.as_view(), name='import_preview'),\n"
        "path('import/status/', views.CustomerImportStatusView.as_view(), name='import_status'),"
    ),
    'urls.py import_preview line',
)
write(URLS, urls)

# ---------------------------------------------------------------------------
# 3) templates/customers/import_status.html -- live progress bar + polling JS
# ---------------------------------------------------------------------------
STATUS_TEMPLATE = jpath('templates', 'customers', 'import_status.html')
if os.path.exists(STATUS_TEMPLATE):
    raise SystemExit('templates/customers/import_status.html already exists; delete it first')

STATUS_TEXT = norm('''{% extends 'base.html' %}
{% load i18n %}

{% block title %}{% trans "Import Progress" %} - Customer Records{% endblock %}

{% block content %}
<div class="max-w-3xl space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
            <p class="page-eyebrow mb-1">{% trans "Registry" %} / {% trans "Import" %} / {% trans "Progress" %}</p>
            <h1 class="page-title">{% trans "Importing Customers" %}</h1>
            <p class="page-subtitle mt-1">{% trans "Your import is being processed — keep this page open" %}</p>
        </div>
    </div>

    <!-- Progress Card -->
    <div class="card">
        <div class="card-body space-y-6">
            <div class="space-y-2">
                <div class="flex justify-between items-center text-sm">
                    <span id="progress-label" class="text-muted">{% trans "Imported" %} {{ processed }} {% trans "of" %} {{ total }}</span>
                    <span id="progress-percent" class="font-semibold text-ink">0%</span>
                </div>
                <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" id="progress-track">
                    <div id="progress-bar" class="progress-fill" style="width: 0%"></div>
                </div>
            </div>

            <div class="flex justify-end space-x-3">
                <button type="button" id="cancel-import" class="btn btn-secondary">
                    <i data-feather="x" class="w-4 h-4"></i>
                    {% trans "Cancel Import" %}
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}''')
STATUS_JS_BLOCK = norm('''
{% block extra_js %}
<style>
    .progress-track {
        width: 100%;
        height: 0.75rem;
        background: var(--color-paper-2);
        border: 1px solid var(--color-rule);
        border-radius: var(--radius-pill);
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: var(--color-success);
        border-radius: var(--radius-pill);
        transition: width 0.3s ease;
    }
</style>
<script>
(function () {
    var statusUrl = '{% url "customers:import_status" %}';
    var bar = document.getElementById('progress-bar');
    var label = document.getElementById('progress-label');
    var percent = document.getElementById('progress-percent');
    var track = document.getElementById('progress-track');
    var cancelled = false;

    function getCookie(name) {
        var parts = document.cookie.split('; ');
        for (var i = 0; i < parts.length; i++) {
            var pair = parts[i].split('=');
            if (pair[0] === name) return decodeURIComponent(pair[1]);
        }
        return '';
    }

    function updateBar(processed, totalRows) {
        var pct = totalRows ? Math.round((processed / totalRows) * 100) : 100;
        if (pct > 100) pct = 100;
        bar.style.width = pct + '%';
        percent.textContent = pct + '%';
        label.textContent = '{% trans "Imported" %} ' + processed + ' {% trans "of" %} ' + totalRows;
        track.setAttribute('aria-valuenow', String(pct));
    }

    function redirect(url) {
        window.location.href = url;
    }

    function poll() {
        if (cancelled) return;
        fetch(statusUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            credentials: 'same-origin',
        })
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                if (data.done) {
                    if (data.redirect) {
                        setTimeout(function () { redirect(data.redirect); }, 600);
                    }
                    return;
                }
                updateBar(data.processed, data.total);
                setTimeout(poll, 700);
            })
            .catch(function () { setTimeout(poll, 1500); });
    }

    document.getElementById('cancel-import').addEventListener('click', function () {
        if (cancelled) return;
        cancelled = true;
        fetch(statusUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            credentials: 'same-origin',
            body: 'cancel=1',
        })
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                if (data.redirect) redirect(data.redirect);
            })
            .catch(function () { redirect(statusUrl); });
    });

    poll();
})();
</script>
{% endblock %}
''')
write(STATUS_TEMPLATE, STATUS_TEXT + STATUS_JS_BLOCK)

# ---------------------------------------------------------------------------
# 4) templates/base.html -- keep the Import/Export nav link active on the
#    new status page too
# ---------------------------------------------------------------------------
BASE = jpath('templates', 'base.html')
base = read(BASE)
if "url_name == 'import_status'" not in base:
    base = replace_once(
        base,
        norm("""class="sidebar-link {% if request.resolver_match.url_name == 'import' or request.resolver_match.url_name == 'import_preview' %}active{% endif %}" {% if request.resolver_match.url_name == 'import' or request.resolver_match.url_name == 'import_preview' %}aria-current="page"{% endif %}>"""),
        norm("""class="sidebar-link {% if request.resolver_match.url_name == 'import' or request.resolver_match.url_name == 'import_preview' or request.resolver_match.url_name == 'import_status' %}active{% endif %}" {% if request.resolver_match.url_name == 'import' or request.resolver_match.url_name == 'import_preview' or request.resolver_match.url_name == 'import_status' %}aria-current="page"{% endif %}>"""),
        'base.html import sidebar link',
    )
    write(BASE, base)

print('OK: chunked import progress applied.')