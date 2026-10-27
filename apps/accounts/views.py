from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.models import Role, UserProfile
from apps.accounts.permissions import require_admin
from apps.workspaces.models import Workspace, WorkspaceMembership


def login_view(request):
    if request.user.is_authenticated:
        return redirect('overview')

    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'overview'
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(next_url)
        else:
            error_message = "Invalid username or password. Please try again."

    return render(request, 'accounts/login.html', {
        'error_message': error_message,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        job_title = request.POST.get('job_title', '').strip()
        phone = request.POST.get('phone', '').strip()
        avatar_color = request.POST.get('avatar_color', profile.avatar_color)
        weekly_capacity = request.POST.get('weekly_capacity_hours', '40')

        try:
            profile.weekly_capacity_hours = max(1, int(weekly_capacity))
        except ValueError:
            pass

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()

        profile.job_title = job_title
        profile.phone = phone
        profile.avatar_color = avatar_color
        profile.save()

        messages.success(request, "Your profile details have been updated.")
        return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'profile': profile,
    })


@require_admin
def users_admin_view(request):
    workspace = Workspace.objects.first()
    memberships = WorkspaceMembership.objects.filter(
        workspace=workspace
    ).select_related('user', 'user__profile').order_by('user__first_name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_role':
            target_user_id = request.POST.get('user_id')
            new_role = request.POST.get('role')
            if new_role in Role.values:
                target_user = get_object_or_404(User, id=target_user_id)
                # Update profile
                profile, _ = UserProfile.objects.get_or_create(user=target_user)
                profile.role = new_role
                profile.save()

                # Update workspace membership
                WorkspaceMembership.objects.filter(
                    workspace=workspace,
                    user=target_user
                ).update(role=new_role)

                messages.success(request, f"Updated role for {target_user.get_full_name() or target_user.username} to {new_role}.")
            return redirect('users_admin')

        elif action == 'create_user':
            username = request.POST.get('username', '').strip().lower()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            role = request.POST.get('role', Role.MEMBER)
            job_title = request.POST.get('job_title', '').strip()
            password = request.POST.get('password', 'WorklineDemo2026!')

            if not username:
                messages.error(request, "Username is required.")
                return redirect('users_admin')

            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists.")
                return redirect('users_admin')

            new_user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            profile, _ = UserProfile.objects.get_or_create(user=new_user)
            profile.role = role
            profile.job_title = job_title
            profile.save()

            if workspace:
                WorkspaceMembership.objects.create(
                    workspace=workspace,
                    user=new_user,
                    role=role
                )

            messages.success(request, f"User '{username}' created successfully.")
            return redirect('users_admin')

    return render(request, 'accounts/users_admin.html', {
        'memberships': memberships,
        'role_choices': Role.choices,
    })
