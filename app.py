import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-fallback-key")

if os.getenv("FLASK_ENV") == "production" and app.config["SECRET_KEY"] == "dev-fallback-key":
    raise RuntimeError("SECRET_KEY must be set in production")

db = SQLAlchemy(app)


# ============================================
# MODELS
# ============================================

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(255))
    category = db.Column(db.String(50))
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<Product {self.name}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    product = db.relationship("Product")

    def __repr__(self):
        return f"<CartItem user={self.user_id} product={self.product_id}>"


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    product = db.relationship("Product")

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_product"),
    )

    def __repr__(self):
        return f"<WishlistItem user={self.user_id} product={self.product_id}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address_line = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order #{self.id} — {self.status}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    product_image = db.Column(db.String(255))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")

    def __repr__(self):
        return f"<OrderItem {self.product_name} x{self.quantity}>"


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    label = db.Column(db.String(30), default="Home")
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80))
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __repr__(self):
        return f"<Address {self.label} — {self.city}>"


# ============================================
# HOOKS / HELPERS
# ============================================

@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id:
        g.user = User.query.get(user_id)
        g.cart_count = CartItem.query.filter_by(user_id=user_id).count()
        g.wishlist_ids = {
            w.product_id
            for w in WishlistItem.query.filter_by(user_id=user_id).all()
        }
    else:
        g.user = None
        g.cart_count = 0
        g.wishlist_ids = set()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ============================================
# PUBLIC ROUTES
# ============================================

@app.route("/")
def home():
    products = Product.query.limit(3).all()
    return render_template("index.html", products=products)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/shop")
def shop():
    categories = request.args.getlist("category")
    prices = request.args.getlist("price")
    sort = request.args.get("sort", "featured")

    query = Product.query

    if categories:
        query = query.filter(Product.category.in_(categories))

    if prices:
        conditions = []
        for p in prices:
            low, high = p.split("-")
            conditions.append(Product.price.between(float(low), float(high)))
        query = query.filter(or_(*conditions))

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "newest":
        query = query.order_by(Product.id.desc())
    else:
        query = query.order_by(func.random())

    products = query.all()
    return render_template("shop.html", products=products)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product.html", product=product)


# ============================================
# AUTH ROUTES
# ============================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not first_name or not last_name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("signup"))

        if password != confirm:
            flash("Passwords don't match.", "error")
            return redirect(url_for("signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("signup"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("That email is already registered.", "error")
            return redirect(url_for("signup"))

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Incorrect email or password.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================================
# DASHBOARD
# ============================================

@app.route("/dashboard")
@login_required
def dashboard():
    orders_count = Order.query.filter_by(user_id=g.user.id).count()
    wishlist_count = WishlistItem.query.filter_by(user_id=g.user.id).count()
    addresses_count = Address.query.filter_by(user_id=g.user.id).count()

    total_spent = db.session.query(func.sum(Order.total)) \
        .filter(Order.user_id == g.user.id) \
        .scalar() or 0

    recent_orders = Order.query \
        .filter_by(user_id=g.user.id) \
        .order_by(Order.created_at.desc()) \
        .limit(3) \
        .all()

    recommended = Product.query.order_by(func.random()).limit(3).all()

    return render_template(
        "dashboard.html",
        user=g.user,
        orders_count=orders_count,
        wishlist_count=wishlist_count,
        addresses_count=addresses_count,
        total_spent=total_spent,
        recent_orders=recent_orders,
        products=recommended,
        active="overview",
    )


@app.route("/dashboard/orders")
@login_required
def dashboard_orders():
    orders = Order.query.filter_by(user_id=g.user.id).order_by(Order.created_at.desc()).all()
    return render_template(
        "dashboard_orders.html",
        user=g.user,
        orders=orders,
        active="orders",
    )


@app.route("/dashboard/orders/<int:order_id>")
@login_required
def dashboard_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != g.user.id:
        abort(403)
    return render_template(
        "dashboard_order_detail.html",
        user=g.user,
        order=order,
        active="orders",
    )


@app.route("/dashboard/addresses")
@login_required
def dashboard_addresses():
    addresses = Address.query.filter_by(user_id=g.user.id) \
        .order_by(Address.is_default.desc(), Address.created_at.desc()).all()
    return render_template(
        "dashboard_addresses.html",
        user=g.user,
        addresses=addresses,
        active="addresses",
    )


@app.route("/dashboard/addresses/new", methods=["GET", "POST"])
@login_required
def address_new():
    if request.method == "POST":
        address = Address(
            user_id=g.user.id,
            label=request.form.get("label", "Home").strip() or "Home",
            full_name=request.form.get("full_name", "").strip(),
            phone=request.form.get("phone", "").strip(),
            address_line1=request.form.get("address_line1", "").strip(),
            address_line2=request.form.get("address_line2", "").strip(),
            city=request.form.get("city", "").strip(),
            state=request.form.get("state", "").strip(),
            postal_code=request.form.get("postal_code", "").strip(),
            country=request.form.get("country", "").strip(),
        )

        required = [address.full_name, address.phone, address.address_line1,
                    address.city, address.postal_code, address.country]
        if not all(required):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("address_new"))

        existing = Address.query.filter_by(user_id=g.user.id).count()
        if existing == 0:
            address.is_default = True
        elif request.form.get("make_default") == "on":
            Address.query.filter_by(user_id=g.user.id, is_default=True).update({"is_default": False})
            address.is_default = True

        db.session.add(address)
        db.session.commit()
        flash("Address saved.", "success")
        return redirect(url_for("dashboard_addresses"))

    return render_template("address_form.html", user=g.user, address=None, active="addresses")


@app.route("/dashboard/addresses/<int:address_id>/edit", methods=["GET", "POST"])
@login_required
def address_edit(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != g.user.id:
        abort(403)

    if request.method == "POST":
        address.label = request.form.get("label", "Home").strip() or "Home"
        address.full_name = request.form.get("full_name", "").strip()
        address.phone = request.form.get("phone", "").strip()
        address.address_line1 = request.form.get("address_line1", "").strip()
        address.address_line2 = request.form.get("address_line2", "").strip()
        address.city = request.form.get("city", "").strip()
        address.state = request.form.get("state", "").strip()
        address.postal_code = request.form.get("postal_code", "").strip()
        address.country = request.form.get("country", "").strip()

        required = [address.full_name, address.phone, address.address_line1,
                    address.city, address.postal_code, address.country]
        if not all(required):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("address_edit", address_id=address.id))

        if request.form.get("make_default") == "on" and not address.is_default:
            Address.query.filter_by(user_id=g.user.id, is_default=True).update({"is_default": False})
            address.is_default = True

        db.session.commit()
        flash("Address updated.", "success")
        return redirect(url_for("dashboard_addresses"))

    return render_template("address_form.html", user=g.user, address=address, active="addresses")


@app.route("/dashboard/addresses/<int:address_id>/delete", methods=["POST"])
@login_required
def address_delete(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != g.user.id:
        abort(403)

    was_default = address.is_default
    db.session.delete(address)
    db.session.commit()

    if was_default:
        next_addr = Address.query.filter_by(user_id=g.user.id).first()
        if next_addr:
            next_addr.is_default = True
            db.session.commit()

    flash("Address removed.", "success")
    return redirect(url_for("dashboard_addresses"))


@app.route("/dashboard/addresses/<int:address_id>/default", methods=["POST"])
@login_required
def address_set_default(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id != g.user.id:
        abort(403)

    Address.query.filter_by(user_id=g.user.id, is_default=True).update({"is_default": False})
    address.is_default = True
    db.session.commit()
    flash("Default address updated.", "success")
    return redirect(url_for("dashboard_addresses"))


@app.route("/dashboard/cards")
@login_required
def dashboard_cards():
    return render_template("dashboard_cards.html", user=g.user, active="cards")


@app.route("/dashboard/settings")
@login_required
def dashboard_settings():
    return render_template("dashboard_settings.html", user=g.user, active="settings")


# ============================================
# CART
# ============================================

@app.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=g.user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in items)
    shipping = 0 if subtotal >= 75 else 8
    total = subtotal + shipping
    return render_template(
        "cart.html",
        user=g.user,
        items=items,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))
    if quantity < 1:
        quantity = 1

    existing = CartItem.query.filter_by(
        user_id=g.user.id, product_id=product_id
    ).first()

    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(user_id=g.user.id, product_id=product_id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    flash(f"{product.name} added to your cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def cart_update(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != g.user.id:
        abort(403)

    quantity = int(request.form.get("quantity", 1))
    if quantity < 1:
        db.session.delete(item)
    else:
        item.quantity = quantity

    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != g.user.id:
        abort(403)

    db.session.delete(item)
    db.session.commit()
    flash("Item removed.", "success")
    return redirect(url_for("cart"))


# ============================================
# WISHLIST
# ============================================

@app.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def wishlist_toggle(product_id):
    product = Product.query.get_or_404(product_id)

    existing = WishlistItem.query.filter_by(
        user_id=g.user.id, product_id=product_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f"{product.name} removed from wishlist.", "success")
    else:
        item = WishlistItem(user_id=g.user.id, product_id=product_id)
        db.session.add(item)
        db.session.commit()
        flash(f"{product.name} added to wishlist.", "success")

    return redirect(request.referrer or url_for("shop"))


@app.route("/dashboard/wishlist")
@login_required
def dashboard_wishlist():
    items = WishlistItem.query.filter_by(user_id=g.user.id).all()
    return render_template(
        "dashboard_wishlist.html",
        user=g.user,
        items=items,
        active="wishlist",
    )


# ============================================
# CHECKOUT
# ============================================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=g.user.id).all()

    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = 0 if subtotal >= 75 else 8
    total = subtotal + shipping

    saved_addresses = Address.query.filter_by(user_id=g.user.id) \
        .order_by(Address.is_default.desc(), Address.created_at.desc()).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address_line = request.form.get("address_line", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        country = request.form.get("country", "").strip()

        if not all([full_name, email, phone, address_line, city, postal_code, country]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("checkout"))

        # Optionally save this address to the address book
        if request.form.get("save_address") == "on":
            make_default = request.form.get("make_default") == "on"
            new_addr = Address(
                user_id=g.user.id,
                label="Home",
                full_name=full_name,
                phone=phone,
                address_line1=address_line,
                city=city,
                postal_code=postal_code,
                country=country,
            )
            existing_count = Address.query.filter_by(user_id=g.user.id).count()
            if existing_count == 0 or make_default:
                Address.query.filter_by(user_id=g.user.id, is_default=True) \
                    .update({"is_default": False})
                new_addr.is_default = True
            db.session.add(new_addr)

        # Create the order
        order = Order(
            user_id=g.user.id,
            full_name=full_name,
            email=email,
            phone=phone,
            address_line=address_line,
            city=city,
            postal_code=postal_code,
            country=country,
            subtotal=subtotal,
            shipping=shipping,
            total=total,
            status="paid",
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product.id,
                product_name=item.product.name,
                product_image=item.product.image,
                unit_price=item.product.price,
                quantity=item.quantity,
            ))

        CartItem.query.filter_by(user_id=g.user.id).delete()
        db.session.commit()

        flash("Order placed successfully.", "success")
        return redirect(url_for("order_confirmation", order_id=order.id))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        saved_addresses=saved_addresses,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )

@app.route("/order/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != g.user.id:
        abort(403)
    return render_template("order_confirmation.html", order=order)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)