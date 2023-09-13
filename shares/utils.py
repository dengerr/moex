from django.shortcuts import render


def htmx_response(request, template, **data):
    is_htmx = request.headers.get('Hx-Request') == 'true'

    if is_htmx:
        return render(request, template, data)
    else:
        return render(request, 'base.html', dict(template=template, **data))
