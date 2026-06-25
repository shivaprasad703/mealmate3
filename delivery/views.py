from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Restaurants, Menu, Cart, Customer
from django.shortcuts import redirect
from django.contrib.auth import logout

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.conf import settings
import razorpay
import random
from django.core.mail import send_mail
from .models import Order, OrderItem



# =========================
# HOME
# =========================
def home(request):
    restaurants = Restaurants.objects.all()   # USE EXISTING DB DATA
    return render(request, "delivery/home.html", {
        "restaurants": restaurants
    })



# =========================
# AUTHENTICATION
# =========================
def sign_up(request):
    return render(request, "delivery/signup.html")


import random
from django.core.mail import send_mail


def handle_signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        address = request.POST.get("address")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("delivery:sign_up")

        otp = random.randint(100000, 999999)

        request.session["signup_data"] = {
            "username": username,
            "password": password,
            "email": email,
            "mobile": mobile,
            "address": address,
            "otp": otp
        }

        # send_mail(
        #     "MealMate Signup OTP",
        #     f"Your OTP is {otp}",
        #     settings.EMAIL_HOST_USER,
        #     [email],
        #     fail_silently=False
        # )

        #messages.success(request, "OTP sent to your email")
        messages.success(request, f"Your OTP is {otp}")
        return redirect("delivery:verify_otp")

    return redirect("delivery:sign_up")



def handle_signin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect("delivery:sign_in")

        otp = random.randint(100000, 999999)

        request.session["login_otp"] = {
            "user_id": user.id,
            "otp": otp
        }

        send_mail(
            "MealMate Login OTP",
            f"Your login OTP is {otp}",
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False
        )

        messages.success(request, "OTP sent to your email")
        return redirect("delivery:login_otp")

    return redirect("delivery:sign_in")




def login_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        data = request.session.get("login_otp")

        if not data:
            messages.error(request, "Session expired. Login again.")
            return redirect("delivery:sign_in")

        if str(data["otp"]) != entered_otp:
            messages.error(request, "Wrong OTP")
            return render(request, "delivery/login_otp.html")

        user = User.objects.get(id=data["user_id"])
        login(request, user)

        del request.session["login_otp"]

        return redirect("delivery:cusdisplay_res", username=user.username)

    return render(request, "delivery/login_otp.html")




from django.contrib import messages

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_data = request.session.get("signup_data")

        if not session_data:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect("delivery:sign_up")

        # ❌ Wrong OTP
        if str(session_data["otp"]) != entered_otp:
            messages.error(request, "❌ Wrong OTP. Please try again.")
            return render(request, "delivery/verify_otp.html")

        # ✅ Correct OTP → Create account
        user = User.objects.create_user(
            username=session_data["username"],
            password=session_data["password"],
            email=session_data["email"]
        )

        Customer.objects.create(
            user=user,
            mobile=session_data["mobile"],
            address=session_data["address"]
        )

        del request.session["signup_data"]

        messages.success(request, "🎉 Account created successfully!")
        return redirect("delivery:sign_in")

    return render(request, "delivery/verify_otp.html")




def sign_in(request):
    return render(request, "delivery/signin.html")





def logout_view(request):
    logout(request)
    return redirect("delivery:home")


# =========================
# PROFILE
# =========================
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

@login_required
def profile(request, username):
    # 🔐 Allow only logged-in user to view their own profile
    if request.user.username != username:
        return HttpResponseForbidden("You are not allowed to view this profile")

    user = get_object_or_404(User, username=username)
    customer = get_object_or_404(Customer, user=user)

    context = {
        "user": user,
        "customer": customer,
        "username": username,
    }
    return render(request, "delivery/profile.html", context)



# =========================
# NAVBAR STATIC PAGES (FIX)
# =========================
def restaurants(request):
    li = Restaurants.objects.all()
    return render(request, "delivery/restaurants.html", {"li": li})


def about(request):
    return render(request, "delivery/about.html")


def contact(request):
    return render(request, "delivery/contact.html")


# =========================
# ADMIN – RESTAURANTS
# =========================


def display_res(request):
    li = Restaurants.objects.all()
    return render(request, "delivery/display_res.html", {"li": li})


# =========================
# CUSTOMER – RESTAURANTS
# =========================
def cusdisplay_res(request, username):
    li = Restaurants.objects.all()
    return render(
        request,
        "delivery/cusdisplay_res.html",
        {"li": li, "username": username},
    )


# =========================
# MENUS
# =========================



def cusmenu(request, id, username):
    res = get_object_or_404(Restaurants, id=id)
    menu = Menu.objects.filter(restaurant=res)
    return render(
        request,
        "delivery/cusmenu.html",
        {"res": res, "menu": menu, "username": username},
    )





def delete_menu(request, item_id):
    menu = get_object_or_404(Menu, id=item_id)
    res_id = menu.restaurant.id
    menu.delete()
    return redirect("delivery:view_menu", res_id=res_id)



# =========================
# CART
# =========================
from django.contrib.auth.decorators import login_required

@login_required(login_url="delivery:sign_in")
def add_to_cart(request, id, username):
    user = request.user
    item = get_object_or_404(Menu, id=id)

    Cart.objects.create(user=user, item=item)
    return redirect(
        "delivery:cusmenu",
        id=item.restaurant.id,
        username=user.username
    )



@login_required(login_url="delivery:sign_in")
def show_cart(request, username):
    user = request.user
    items = Cart.objects.filter(user=user)
    total_price = sum(i.item.price for i in items)

    return render(
        request,
        "delivery/cart.html",
        {
            "items": items,
            "total_price": total_price,
            "username": user.username,
        },
    )


@login_required
def checkout(request, username):
    user = request.user   # simpler & correct
    cart_items = Cart.objects.filter(user=user)

    if not cart_items.exists():
        return redirect("delivery:cusdisplay_res", username=username)

    total_price = sum(item.item.price for item in cart_items)
    amount = int(total_price * 100)  # Razorpay works in paise

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    payment = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, "delivery/checkout.html", {
        "username": username,
        "cart_items": cart_items,
        "total_price": total_price,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "order_id": payment["id"],
    })




# =========================
# ORDERS
# =========================
def orders(request, username):
    return render(request, "delivery/orders.html", {"username": username})






def admin_login(request):
    # Already logged in admin → dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("delivery:admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect("delivery:admin_dashboard")
            else:
                messages.error(request, "You are not authorized as admin.")
        else:
            messages.error(request, "Invalid username or password.")

    # ✅ CORRECT TEMPLATE PATH
    return render(request, "delivery/admin-panel/login.html")






@login_required(login_url="delivery:admin_login")
def admin_dashboard(request):
    return render(request, "delivery/admin-panel/dashboard.html")







@login_required(login_url="delivery:admin_login")
def admin_restaurants(request):
    restaurants = Restaurants.objects.all()
    return render   (
    request,
    "delivery/admin-panel/restaurants.html",
    {"restaurants": restaurants}
)

@login_required(login_url="delivery:admin_login")
def delete_res(request, id):
    restaurant = get_object_or_404(Restaurants, id=id)
    restaurant.delete()
    return redirect("delivery:admin_restaurants")


@login_required(login_url="delivery:admin_login")
def add_res(request):
    if request.method == "POST":
        Restaurants.objects.create(
            Res_name=request.POST.get("res_name"),   # ✅ MATCH HTML
            Food_cat=request.POST.get("food_cat"),   # ✅ MATCH HTML
            rating=request.POST.get("rating"),
            img=request.POST.get("img"),
            address=request.POST.get("address"),
        )
        return redirect("delivery:admin_restaurants")

    return render(request, "delivery/admin-panel/add_res.html")



@login_required(login_url="delivery:admin_login")
def view_menu(request, res_id):
    restaurant = Restaurants.objects.get(id=res_id)
    items = Menu.objects.filter(restaurant=restaurant)

    return render(
        request,
        "delivery/admin-panel/view_items.html",
        {
            "restaurant": restaurant,
            "items": items
        }
    )


@login_required(login_url="delivery:admin_login")
def add_menu(request, res_id):
    restaurant = Restaurants.objects.get(id=res_id)

    if request.method == "POST":
        Menu.objects.create(
            restaurant=restaurant,
            item_name=request.POST["item_name"],
            price=request.POST["price"],
            #   
        )
        return redirect("delivery:view_menu", res_id=res_id)

    return render(
        request,
        "delivery/admin-panel/add_item.html",
        {"restaurant": restaurant}
    )


# delivery/views.py



@login_required(login_url="delivery:admin_login")







def admin_logout(request):
    logout(request)
    return redirect("delivery:admin_login")
# def home(request):
#     return render(request, "home.html")





@login_required(login_url="delivery:admin_login")
def view_menu(request, res_id):
    restaurant = get_object_or_404(Restaurants, id=res_id)
    items = Menu.objects.filter(restaurant=restaurant)

    return render(
        request,
        "delivery/admin-panel/view_items.html",
        {
            "restaurant": restaurant,
            "items": items
        }
    )


@login_required(login_url="delivery:admin_login")
def add_menu(request, res_id):
    restaurant = get_object_or_404(Restaurants, id=res_id)

    if request.method == "POST":
        Menu.objects.create(
            restaurant=restaurant,
            item_name=request.POST.get("item_name"),
            description=request.POST.get("description"),
            price=request.POST.get("price"),
            category=request.POST.get("category"),
            is_available=True if request.POST.get("is_available") else False,
            image=request.FILES.get("image")  # 🔥 IMAGE
        )
        return redirect("delivery:view_menu", res_id=res_id)

    return render(
        request,
        "delivery/admin-panel/add_item.html",
        {"restaurant": restaurant}
    )


def remove_from_cart(request, id, username):
    cart_item = get_object_or_404(Cart, id=id)
    cart_item.delete()
    return redirect("delivery:show_cart", username=username)



    # 3️⃣ CLEAR CART
    cart_items.delete()

    messages.success(request, "Order placed successfully!")

    return redirect("delivery:my_orders", username=username)



@login_required
def my_orders(request, username):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")

    return render(
        request,
        "delivery/my_orders.html",
        {"orders": orders, "username": username}
    )


@login_required(login_url="delivery:admin_login")
def admin_orders(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(
        request,
        "delivery/admin-panel/orders.html",
        {"orders": orders}
    )


def payment_success(request, username):
    if request.method == "POST":
        user = request.user
        cart_items = Cart.objects.filter(user=user)
        total_price = sum(i.item.price for i in cart_items)

        order = Order.objects.create(
            user=user,
            total_amount=total_price,
            status="Paid"
        )

        for cart in cart_items:
            OrderItem.objects.create(
    order=order,
    menu_item=cart.item,
    price=cart.item.price
)


        cart_items.delete()
        return redirect("delivery:my_orders", username=username)

@login_required(login_url="delivery:admin_login")
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save()

        messages.success(request, "Order status updated")
        return redirect("delivery:admin_orders")

    return render(
        request,
        "delivery/admin-panel/update_order_status.html",
        {"order": order}
    )
