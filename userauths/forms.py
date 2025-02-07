from django import forms
from django.contrib.auth.forms import UserCreationForm
import bcrypt

from userauths.models import User, Profile  

USER_TYPE = (
    ("Vendor", "Vendor"),
    ("Customer", "Customer"),
)

class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Full Name'}),
        required=True
    )
    mobile = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Mobile Number'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Email Address'}),
        required=True
    )
    user_type = forms.ChoiceField(
        choices=USER_TYPE,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        # Hash password using bcrypt
        hashed_password = bcrypt.hashpw(password1.encode('utf-8'), bcrypt.gensalt())
        cleaned_data["hashed_password"] = hashed_password.decode('utf-8')

        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Use the hashed password from the cleaned data
        user.password = self.cleaned_data["hashed_password"]

        if commit:
            user.save()
            # Create the Profile instance
            Profile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                mobile=self.cleaned_data["mobile"],
                user_Type=self.cleaned_data["user_type"]
            )
        return user

class LoginForm(forms.Form):
   email = forms.EmailField(
        widget=forms.TextInput(attrs={'class':'form-control rounded','placeholder':'Email Address'}),
        required= True
    )
   password= forms.CharField(
        widget=forms.PasswordInput(attrs={'class':'form-control rounded','placeholder':'Password'}),
        required= True
    )
   
   class Meta:
       model = User
       fields = ['email','password']
    