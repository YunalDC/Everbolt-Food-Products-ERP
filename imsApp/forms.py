from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm, UserChangeForm
from django.contrib.auth.models import User
from more_itertools import quantify
from .models import Category, Product, Stock, Invoice, Invoice_Item
from datetime import datetime

class UserRegistration(UserCreationForm):
    email = forms.EmailField(max_length=250,help_text="The email field is required.")
    first_name = forms.CharField(max_length=250,help_text="The First Name field is required.")
    last_name = forms.CharField(max_length=250,help_text="The Last Name field is required.")

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2', 'first_name', 'last_name')
    

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email = email)
        except Exception as e:
            return email
        raise forms.ValidationError(f"The {user.email} mail is already exists/taken")

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            user = User.objects.get(username = username)
        except Exception as e:
            return username
        raise forms.ValidationError(f"The {user.username} mail is already exists/taken")


class UpdateProfile(UserChangeForm):
    username = forms.CharField(max_length=250,help_text="The Username field is required.")
    email = forms.EmailField(max_length=250,help_text="The Email field is required.")
    first_name = forms.CharField(max_length=250,help_text="The First Name field is required.")
    last_name = forms.CharField(max_length=250,help_text="The Last Name field is required.")
    current_password = forms.CharField(max_length=250)

    class Meta:
        model = User
        fields = ('email', 'username','first_name', 'last_name')

    def clean_current_password(self):
        if not self.instance.check_password(self.cleaned_data['current_password']):
            raise forms.ValidationError(f"Password is Incorrect")

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.exclude(id=self.cleaned_data['id']).get(email = email)
        except Exception as e:
            return email
        raise forms.ValidationError(f"The {user.email} mail is already exists/taken")

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            user = User.objects.exclude(id=self.cleaned_data['id']).get(username = username)
        except Exception as e:
            return username
        raise forms.ValidationError(f"The {user.username} mail is already exists/taken")

class UpdatePasswords(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control form-control-sm rounded-0'}), label="Old Password")
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control form-control-sm rounded-0'}), label="New Password")
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control form-control-sm rounded-0'}), label="Confirm New Password")
    class Meta:
        model = User
        fields = ('old_password','new_password1', 'new_password2')

class SaveCategory(forms.ModelForm):
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.Textarea)
    status = forms.ChoiceField(choices=[('1', 'Active'), ('2', 'Inactive')])

    class Meta:
        model = Category
        fields = ('name', 'description', 'status')

    def clean_name(self):
        id = self.instance.id if self.instance.id else 0
        name = self.cleaned_data['name']

        qs = Category.objects.filter(name=name)
        if id:
            qs = qs.exclude(id=id)

        if qs.exists():
            raise forms.ValidationError(f"{name} Category Already Exists.")
        return name


class SaveProduct(forms.ModelForm):
    # Optional: override some fields for better widgets/labels
    name = forms.CharField(max_length=250)
    description = forms.CharField(widget=forms.Textarea)
    status = forms.ChoiceField(choices=[('1', 'Active'), ('2', 'Inactive')])
    image = forms.ImageField(required=False)   # assumes Product has an ImageField

    class Meta:
        model = Product
        fields = ('category', 'code', 'name', 'description', 'price', 'image', 'status')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active categories in dropdown (change filter if you want all)
        self.fields['category'].queryset = Category.objects.filter(status='1').order_by('name')
        self.fields['category'].empty_label = '-- Select Category --'

    def clean_code(self):
        id = self.instance.id if self.instance.id else 0
        code = self.cleaned_data['code']

        qs = Product.objects.filter(code=code)
        if id:
            qs = qs.exclude(id=id)

        if qs.exists():
            raise forms.ValidationError(f"{code} already exists.")
        return code
    
class SaveStock(forms.ModelForm):

    # These fields must match the POST names in your HTML
    product = forms.CharField()   # will convert id → Product instance
    quantity = forms.FloatField(min_value=0.01)

    type = forms.ChoiceField(
        choices=(('1', 'Stock-in'), ('2', 'Stock-Out')),
        label='Transaction Type'
    )

    # Must match your model + your HTML select names
    product_type = forms.ChoiceField(
        choices=(
            ('Finished', 'Finished'),
            ('Packing', 'Packing'),
            ('Raw', 'Raw'),
        ),
        required=False
    )

    reason = forms.CharField(
        max_length=100,
        required=False
    )

    unit = forms.CharField(
        max_length=20,
        required=False
    )

    class Meta:
        model = Stock
        fields = (
            'product',
            'quantity',
            'type',
            'product_type',
            'reason',
            'unit',
        )

    def clean_product(self):
        """
        Convert product ID string → Product instance.
        """
        pid = self.cleaned_data.get('product')

        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            raise forms.ValidationError("Invalid product ID")

        try:
            return Product.objects.get(id=pid_int)
        except Product.DoesNotExist:
            raise forms.ValidationError("Product does not exist")

class SaveInvoice(forms.ModelForm):
    transaction = forms.CharField(max_length=100)
    customer = forms.CharField(max_length=250)
    total = forms.FloatField()

    class Meta:
        model = Invoice
        fields = ('transaction', 'customer', 'total')

    def clean_transaction(self):
        pref = datetime.today().strftime('%Y%m%d')
        transaction= ''
        code = str(1).zfill(4)
        while True:
            invoice = Invoice.objects.filter(transaction=str(pref + code)).count()
            if invoice > 0:
                code = str(int(code) + 1).zfill(4)
            else:
                transaction = str(pref + code)
                break
        return transaction

class SaveInvoiceItem(forms.ModelForm):
    invoice = forms.CharField(max_length=30)
    product = forms.CharField(max_length=30)
    quantity = forms.CharField(max_length=100)
    price = forms.CharField(max_length=100)

    class Meta:
        model = Invoice_Item
        fields = ('invoice','product','quantity','price')

    def clean_invoice(self):
        iid = self.cleaned_data['invoice']
        try:
            invoice = Invoice.objects.get(id=iid)
            return invoice
        except:
            raise forms.ValidationError("Invoice ID is not valid")

    def clean_product(self):
        pid = self.cleaned_data['product']
        try:
            product = Product.objects.get(id=pid)
            return product
        except:
            raise forms.ValidationError("Product is not valid")

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty.isnumeric():
            return int(qty)
        raise forms.ValidationError("Quantity is not valid")
    




