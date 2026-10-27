from django.shortcuts import render, redirect


def root_redirect_view(request):
    """
    Root URL redirect handler:
    - Logged-out visitors navigating to '/' are redirected to the login page.
    - Authenticated users navigating to '/' are redirected to the Overview dashboard.
    """
    if request.user.is_authenticated:
        return redirect('overview')
    return redirect('login')


def handler403(request, exception=None):
    return render(request, 'errors/403.html', {'exception': exception}, status=403)


def handler404(request, exception=None):
    return render(request, 'errors/404.html', {'exception': exception}, status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)
