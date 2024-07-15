from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from installment_data import data_set_1, data_set_2

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create DataFrame for additional devices
additional_devices = pd.DataFrame([
    ["Sensore di apertura", 79, 25, 39.0, 10],
    ["2 sensori di apertura", 119, 35, 59.0, 10],
    ["Sensore di movimento a tenda", 119, 35, 59.0, 10],
    ["Sensore di movimento con fotocamera", 249, 50, 124.0, 10],
    ["2 sensori di movimento con fotocamera", 379, 80, 189.0, 10],
    ["Sensore di movimento", 119, 35, 59.0, 10],
    ["Sensore di movimento esterno con fotocamera", 399, 80, 199.0, 20],
    ["2 sensori di movimento esterno con fotocamera", 699, 120, 349.0, 20],
    ["Sirena interna", 159, 50, 79.0, 10],
    ["Sirena esterna", 189, 50, 94.0, 10],
    ["Telecomando", 79, 25, 39.0, 10],
    ["SOS antipanico", 79, 25, 39.0, 10],
    ["Rilevatore di fumo", 129, 35, 64.0, 10],
    ["Rilevatore di allagamento", 99, 25, 49.0, 10],
    ["Rilevatore di gas", 179, 50, 89.0, 10],
    ["Presa SMART", 139, 35, 69.0, 10],
    ["Rilevatore qualita dell'aria", 119, 35, 59.0, 10],
    ["Tastiera", 179, 50, 89.0, 10],
    ["Ripetitore di segnale wireless", 119, 35, 59.0, 10],
    ["Modulo voce", 159, 35, 79.0, 10],
    ["Campanello", 159, 35, 79.0, 10],
    ["Modulo voce e Campanello", 219, 50, 109.0, 10]
], columns=['aditional devices', 'price', 'commission', 'discount price', 'discount commission'])

df1 = pd.DataFrame(data_set_1, columns=['Total cost', 'months', 'Installment amount'])
df2 = pd.DataFrame(data_set_2, columns=['Total cost', 'months', 'Installment amount'])


df1['Total cost'] = df1['Total cost'].str.replace(' €', '').str.replace(',', '').astype(float)
df2['Total cost'] = df2['Total cost'].str.replace(' €', '').str.replace(',', '').astype(float)


df1['Installment amount'] = df1['Installment amount'].astype(float)
df2['Installment amount'] = df2['Installment amount'].astype(float)

def get_installment_amount(total_cost, months, data):
    rounded_cost = round(total_cost / 50) * 50
    matching_row = data[(data['Total cost'] == rounded_cost) & (data['months'] == months)]
    return matching_row['Installment amount'].values[0] if not matching_row.empty else None



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('signup'))
        
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('calculate'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def calculate():
    total_cost = 0
    commission_mixed = 0
    commission_zero = 0
    commission_no_fin = 0
    installment_1 = None
    installment_2 = None
    selected_months = 0
    selected_devices = []
    discount_applied = False

    if request.method == 'POST':
        residence = int(request.form.get('residence', 0))
        kit_base = int(request.form.get('kit_base', 0))
        selected_months = int(request.form.get('months', 0))
        selected_devices = request.form.getlist('additional_devices')
        discount_applied = 'apply_discount' in request.form

        # Calculate base total cost
        total_cost = (selected_months * residence) + kit_base

        # Add additional devices cost and commission
        for device in selected_devices:
            device_data = additional_devices[additional_devices['aditional devices'] == device].iloc[0]
            if discount_applied:
                total_cost += device_data['discount price']
                commission_mixed += device_data['discount commission']
                commission_zero += device_data['discount commission']
            else:
                total_cost += device_data['price']
                commission_mixed += device_data['commission']
                commission_zero += device_data['commission']

        # Calculate commissions based on total cost
        if 2500 <= total_cost <= 2950:
            commission_mixed += 450
            commission_zero += 350
        elif 3000 <= total_cost <= 4000:
            commission_mixed += 650
            commission_zero += 500
        elif total_cost > 4000:
            commission_mixed += 850
            commission_zero += 700
        elif total_cost <= 1000:
            if total_cost == 999:
                commission_no_fin = 450
            elif total_cost == 899:
                commission_no_fin = 400
            elif total_cost == 799:
                commission_no_fin = 300

        # Get installment amounts for both datasets
        if selected_months in [48, 54, 60]:
            installment_1 = get_installment_amount(total_cost, selected_months, df1)
            installment_2 = get_installment_amount(total_cost, selected_months, df2)

    return render_template('index.html', 
                           total_cost=total_cost, 
                           commission_mixed=commission_mixed, 
                           commission_zero=commission_zero,
                           commission_no_fin=commission_no_fin,
                           installment_1=installment_1,
                           installment_2=installment_2,
                           selected_months=selected_months,
                           additional_devices=additional_devices['aditional devices'].tolist(),
                           selected_devices=selected_devices,
                           discount_applied=discount_applied)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)