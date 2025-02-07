from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.sessions.models import Session
import bcrypt  

from userauths import models as userauths_models
from userauths import forms as userauths_forms
from vendor import models as vendor_models



def register_view(request):
    if request.session.get('user_id'):
        messages.warning(request, "You are already logged in")
        return redirect('/')
    
    form = userauths_forms.UserRegistrationForm(request.POST or None)

    if form.is_valid():
        full_name = form.cleaned_data.get('full_name')
        email = form.cleaned_data.get('email')
        mobile = form.cleaned_data.get('mobile')
        password = form.cleaned_data.get('password1')  # Raw password
        user_type = form.cleaned_data.get("user_type")

        # Check if email already exists
        if userauths_models.User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered")
            return redirect('/register')
        
        # Hash password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create the user object (with only the fields from AbstractUser)
        user = userauths_models.User.objects.create(
            email=email,
            password=hashed_password.decode('utf-8')  # Store hashed password
        )

        # Create the profile with full_name, mobile, and other info
        profile = userauths_models.Profile.objects.create(
            user=user,
            full_name=full_name,
            mobile=mobile
        )

        # Assign the user type and create vendor if necessary
        if user_type == "Vendor":
            vendor_models.Vendor.objects.create(user=user, store_name=full_name)
            profile.user_type = "Vendor"
        else:
            profile.user_type = "Customer"

        profile.save()

        # Success message and redirect to login page
        messages.success(request, "Account was created successfully.")
        return redirect('/login/')
    
    return render(request, 'userauths/sign-up.html', {'form': form})


def login_view(request):
    if request.session.get('user_id'):
        messages.warning(request, "You are already logged in")
        return redirect('store:index')  # Adjusted redirect path as needed
    
    if request.method == 'POST':
        form = userauths_forms.LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                user = userauths_models.User.objects.get(email=email)

                if bcrypt.checkpw(password.encode(), user.password.encode()):
                    request.session['user_id'] = user.id
                    request.session['user_email'] = user.email

                    messages.success(request, "You are logged in")
                    return redirect('store:index')  # Redirect to store index or wherever
                else:
                    messages.error(request, "Invalid email or password")

            except userauths_models.User.DoesNotExist:
                messages.error(request, "User does not exist")
        else:
            messages.error(request, "Please correct the errors in the form")

    else:
        form = userauths_forms.LoginForm()  # Create an empty form if GET request
    
    return render(request, "userauths/sign-in.html", {'form': form})

def logout_view(request):
    # Preserve the cart_id before logging out
    if 'cart_id' in request.session:
        cart_id = request.session['cart_id']
    else:
        cart_id = None

    # Clear user-specific session data
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'user_email' in request.session:
        del request.session['user_email']

    # Restore the cart_id after clearing the session
    request.session['cart_id'] = cart_id

    # Show logout message
    messages.success(request, "You have been logged out successfully.")

    # Redirect to sign-in page
    return redirect("userauths:sign-in")
