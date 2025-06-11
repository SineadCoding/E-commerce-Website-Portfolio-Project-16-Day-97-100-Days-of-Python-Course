from flask import Flask, session, request, jsonify, render_template, redirect, url_for, get_flashed_messages
import stripe
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

DOMAIN = "http:Jungle-in-a-Pot/"

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (  
        username text,  
        email text,  
        password text  
        )""")

conn.commit()
conn.close()


shopping_cart = {}


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/shop')
def shop():
    return render_template("shop.html")


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    item_name = request.form['item_name']
    item_price = float(request.form['item_price'])
    quantity = int(request.form['quantity'])
    image = request.form['image']

    if item_name in shopping_cart:
        shopping_cart[item_name]['quantity'] += quantity
    else:
        shopping_cart[item_name] = {'price': item_price, 'quantity': quantity, 'image': image}

    return redirect(url_for('shop'))


@app.route('/cart')
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template("cart.html", cart=shopping_cart)


@app.route('/delete_item', methods=['POST'])
def delete_item():
    if 'username' not in session:
        return redirect(url_for('login'))

    item_name = request.form['item_name']

    print(item_name)

    if item_name in shopping_cart:
        del shopping_cart[item_name]

    return redirect(url_for('cart'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return 'Passwords do not match'

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            return 'Username already exists'

        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, email, hashed_password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['username'] = username
            return redirect(url_for('home'))

        return 'Invalid username or password'

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/create-checkout-session', methods=['GET', 'POST'])
def create_checkout_session():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'delivery_details' not in session:
        return redirect(url_for('delivery'))

    if not shopping_cart:
        return 'Your shopping cart is empty'

    try:
        items = []
        for item, values in shopping_cart.items():
            items.append({
                'price_data': {
                    'currency': 'zar',
                    'unit_amount': int(values['price'] * 100),
                    'product_data': {
                        'name': item,
                    },
                },
                'quantity': values['quantity'],
            })
        print("Items:", items)

        checkout_session = stripe.checkout.Session.create(
            line_items=items,
            mode='payment',
            success_url=DOMAIN + '/success',
            cancel_url=DOMAIN + '/cancel',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


@app.route('/success')
def success():
    shopping_cart.clear()
    return render_template('success.html')


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        delivery_date = request.form['delivery_date']
        delivery_time = request.form['delivery_time']

        # Save delivery details to database or session
        session['delivery_details'] = {
            'address': address,
            'city': city,
            'state': state,
            'zip_code': zip_code,
        }

        return redirect(url_for('create_checkout_session'))

    return render_template('delivery.html')


@app.context_processor
def inject_login_logout():
    return dict(login_logout=(
        '<a href="/login" style="text-decoration: none;">'
        '<button class="button" style="padding: 8px 20px; background-color: #FFFFFF; color: #000000; border: none; border-radius: 5px; cursor: pointer; vertical-align: middle; margin: 0 8px">Login</button>'
        '</a>'
        if 'username' not in session else
        '<a href="/logout" style="text-decoration: none;">'
        '<button class="button" style="padding: 8px 20px; background-color: #FFFFFF; color: #000000; border: none; border-radius: 5px; cursor: pointer; vertical-align: middle; margin: 0 8px">Logout</button>'
        '</a>'
    ), register=(
        '<a href="/register" style="text-decoration: none;">'
        '<button class="button" style="padding: 8px 20px; background-color: #98FB98; color: #FFFFFF; border: none; border-radius: 5px; cursor: pointer; vertical-align: middle; margin: 0 8px">Register</button>'
        '</a>'
    ))


if __name__ == '__main__':
    app.run()
