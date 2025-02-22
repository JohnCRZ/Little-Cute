import tkinter as tk
from tkinter import ttk, messagebox
from database import create_connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import os
import csv
from datetime import datetime

# --- API Key for ExchangeRate-API ---
API_KEY = 'fd0c334e5e3508245558e420'
BASE_CURRENCY = 'CNY'

# --- Global Variables ---
exchange_rates = None

# --- Helper Functions ---

def get_exchange_rates(base_currency=BASE_CURRENCY):
    """Fetch exchange rates from API."""
    url = f'https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency}'
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        return data['conversion_rates']
    else:
        raise Exception("Failed to fetch exchange rates")

def convert_to_base(amount, currency, rates):
    """Convert amount to base currency."""
    if currency == BASE_CURRENCY:
        return amount
    rate = rates.get(currency)
    if rate:
        return amount / rate
    else:
        raise Exception(f"Exchange rate for {currency} not found")

def send_notification(message):
    """Send macOS notification."""
    os.system(f'osascript -e \'display notification "{message}" with title "Little Cute"\'')
    print(f"Notification sent: {message}")

# --- Database Initialization ---

def initialize_database():
    """Initialize the database with necessary tables."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            platform TEXT,
            amount REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            expiration_date TEXT,
            currency TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investment_id INTEGER,
            update_date TEXT NOT NULL,
            profit_loss REAL NOT NULL,
            FOREIGN KEY (investment_id) REFERENCES investments (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- GUI Functions ---

def add_investment():
    """Save the investment data to the database."""
    name = name_entry.get()
    amount = amount_entry.get()
    if not name or not amount:
        tk.messagebox.showerror("Error", "Please fill in the name and amount.")
        return
    platform = platform_entry.get() if platform_entry.get() else "Unknown"
    purchase_date = purchase_date_entry.get() if purchase_date_entry.get() else datetime.today().strftime('%Y-%m-%d')
    expiration_date = expiration_date_entry.get() if expiration_date_entry.get() else None
    currency = currency_combobox.get()
    category = category_combobox.get()
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO investments (name, platform, amount, purchase_date, expiration_date, currency, category, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, platform, amount, purchase_date, expiration_date, currency, category, 'Active'))
    conn.commit()
    conn.close()
    tk.messagebox.showinfo("Success", "Investment added successfully.")

def load_investments(tree):
    """Load all investments from the database and display them in the Treeview."""
    for item in tree.get_children():
        tree.delete(item)
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investments")
    investments = cursor.fetchall()
    conn.close()
    for investment in investments:
        tree.insert("", "end", values=investment)

def delete_investment(tree):
    """Delete the selected investment from the database."""
    selected_item = tree.selection()
    if not selected_item:
        tk.messagebox.showerror("Error", "No investment selected.")
        return
    investment_id = tree.item(selected_item)['values'][0]
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM updates WHERE investment_id = ?", (investment_id,))
    cursor.execute("DELETE FROM investments WHERE id = ?", (investment_id,))
    conn.commit()
    conn.close()
    load_investments(tree)
    tk.messagebox.showinfo("Success", "Investment deleted successfully.")

def update_profit_loss():
    """Save the profit/loss update to the database."""
    investment_id = investment_combobox.get().split(' - ')[0]
    profit_loss = profit_loss_entry.get()
    update_date = update_date_entry.get()
    if not investment_id or not profit_loss or not update_date:
        tk.messagebox.showerror("Error", "Please fill in all fields.")
        return
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO updates (investment_id, update_date, profit_loss)
        VALUES (?, ?, ?)
    ''', (investment_id, update_date, profit_loss))
    conn.commit()
    conn.close()
    tk.messagebox.showinfo("Success", "Profit/Loss updated successfully.")

def generate_pie_chart(frame):
    """Generate a pie chart showing asset distribution by category."""
    global exchange_rates
    rates = exchange_rates
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, amount, currency FROM investments")
    investments = cursor.fetchall()
    conn.close()
    if not investments:
        tk.messagebox.showinfo("Info", "No investments available to display chart.")
        return
    categories = {}
    for category, amount, currency in investments:
        try:
            amount_in_base = convert_to_base(float(amount), currency, rates)
            if category in categories:
                categories[category] += amount_in_base
            else:
                categories[category] = amount_in_base
        except ValueError as e:
            tk.messagebox.showerror("Error", f"Invalid amount data: {e}")
            return
    labels = list(categories.keys())
    sizes = list(categories.values())
    for widget in frame.winfo_children():
        widget.destroy()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    # Pack the frame and the canvas widget
    frame.pack(fill='both', expand=True, padx=10, pady=10)
    canvas.get_tk_widget().pack(fill='both', expand=True)

def close_chart(frame):
    """Close the pie chart by clearing the frame and removing it from layout."""
    for widget in frame.winfo_children():
        widget.destroy()
    frame.pack_forget()
    root.update()  # Force window to update layout

def calculate_totals(view_reports_tab):
    """Calculate and display total assets and profit/loss in base currency, then remove after 1 minute."""
    global exchange_rates
    rates = exchange_rates
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT amount, currency FROM investments")
    investments = cursor.fetchall()
    cursor.execute("SELECT u.profit_loss, i.currency FROM updates u JOIN investments i ON u.investment_id = i.id")
    updates = cursor.fetchall()
    conn.close()
    total_assets = sum(convert_to_base(float(amount), currency, rates) for amount, currency in investments)
    total_profit_loss = sum(convert_to_base(float(profit_loss), currency, rates) for profit_loss, currency in updates)
    totals_frame = ttk.Frame(view_reports_tab)
    totals_frame.pack(pady=5)
    tk.Label(totals_frame, text=f"Total Assets ({BASE_CURRENCY}): {total_assets:.2f}").pack(side='left', padx=10)
    tk.Label(totals_frame, text=f"Total Profit/Loss ({BASE_CURRENCY}): {total_profit_loss:.2f}").pack(side='left', padx=10)
    # Remove the totals frame after 1 minute (60000 milliseconds)
    root.after(60000, totals_frame.destroy)

def load_analysis(tree):
    """Load analysis data into the Treeview with base currency conversions."""
    global exchange_rates
    rates = exchange_rates
    for item in tree.get_children():
        tree.delete(item)
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, i.name, i.amount, i.currency, COALESCE(SUM(u.profit_loss), 0) as total_profit_loss
        FROM investments i
        LEFT JOIN updates u ON i.id = u.investment_id
        GROUP BY i.id, i.name, i.amount, i.currency
    ''')
    analysis_data = cursor.fetchall()
    conn.close()
    for data in analysis_data:
        id, name, amount, currency, total_profit_loss = data
        amount_in_base = convert_to_base(float(amount), currency, rates)
        profit_loss_in_base = convert_to_base(float(total_profit_loss), currency, rates)
        rate_of_return = (profit_loss_in_base / amount_in_base * 100) if amount_in_base != 0 else 0
        tree.insert("", "end", values=(id, name, f"{profit_loss_in_base:.2f}", f"{rate_of_return:.2f}%"))

def update_investment_combobox():
    """Update the investment combobox with the latest investments."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM investments")
    investments = cursor.fetchall()
    conn.close()
    investment_combobox['values'] = [f"{inv[0]} - {inv[1]}" for inv in investments]

def check_expired_investments():
    """Move expired investments to pending status."""
    today = datetime.today().strftime('%Y-%m-%d')
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE investments
        SET status = 'Pending'
        WHERE expiration_date < ? AND status = 'Active'
    ''', (today,))
    conn.commit()
    conn.close()

def export_to_csv():
    """Export investment data to CSV."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investments")
    investments = cursor.fetchall()
    cursor.execute("SELECT * FROM updates")
    updates = cursor.fetchall()
    conn.close()
    with open('investments.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Platform", "Amount", "Purchase Date", "Expiration Date", "Currency", "Category", "Status"])
        writer.writerows(investments)
        writer.writerow([])
        writer.writerow(["Update ID", "Investment ID", "Update Date", "Profit/Loss"])
        writer.writerows(updates)
    tk.messagebox.showinfo("Success", "Data exported to investments.csv")

# --- Main Window Creation ---

def create_main_window():
    """Create the main GUI window with tabs."""
    global exchange_rates
    exchange_rates = get_exchange_rates()
    global root
    root = tk.Tk()
    root.title("Little Cute - Investment Manager")
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    # Add Investment Tab
    add_investment_tab = ttk.Frame(notebook)
    notebook.add(add_investment_tab, text='Add Investment')

    tk.Label(add_investment_tab, text="Product Name:").grid(row=0, column=0, padx=10, pady=10)
    global name_entry
    name_entry = tk.Entry(add_investment_tab)
    name_entry.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Platform:").grid(row=1, column=0, padx=10, pady=10)
    global platform_entry
    platform_entry = tk.Entry(add_investment_tab)
    platform_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Amount:").grid(row=2, column=0, padx=10, pady=10)
    global amount_entry
    amount_entry = tk.Entry(add_investment_tab)
    amount_entry.grid(row=2, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Purchase Date (YYYY-MM-DD):").grid(row=3, column=0, padx=10, pady=10)
    global purchase_date_entry
    purchase_date_entry = tk.Entry(add_investment_tab)
    purchase_date_entry.grid(row=3, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Expiration Date (YYYY-MM-DD, optional):").grid(row=4, column=0, padx=10, pady=10)
    global expiration_date_entry
    expiration_date_entry = tk.Entry(add_investment_tab)
    expiration_date_entry.grid(row=4, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Currency:").grid(row=5, column=0, padx=10, pady=10)
    global currency_combobox
    currency_combobox = ttk.Combobox(add_investment_tab, values=["CNY", "USD"])
    currency_combobox.set(BASE_CURRENCY)
    currency_combobox.grid(row=5, column=1, padx=10, pady=10)

    tk.Label(add_investment_tab, text="Category:").grid(row=6, column=0, padx=10, pady=10)
    global category_combobox
    category_combobox = ttk.Combobox(add_investment_tab,
                                     values=["Cash", "Funds", "Stocks", "Bonds", "US Dollars", "Gold"])
    category_combobox.set("Other")
    category_combobox.grid(row=6, column=1, padx=10, pady=10)

    save_button = tk.Button(add_investment_tab, text="Save Investment", command=add_investment)
    save_button.grid(row=7, column=0, columnspan=2, pady=10)

    # View Reports Tab
    view_reports_tab = ttk.Frame(notebook)
    notebook.add(view_reports_tab, text='View Reports')

    columns = ("ID", "Name", "Platform", "Amount", "Purchase Date", "Expiration Date", "Currency", "Category", "Status")
    tree = ttk.Treeview(view_reports_tab, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    tree.pack(fill='x', padx=10, pady=10)

    load_investments(tree)
    calculate_totals(view_reports_tab)

    global chart_frame
    chart_frame = ttk.Frame(view_reports_tab)  # Create frame, don't pack yet

    button_frame = ttk.Frame(view_reports_tab)
    button_frame.pack(pady=5)
    refresh_button = tk.Button(button_frame, text="Refresh Investments", command=lambda: [load_investments(tree), calculate_totals(view_reports_tab)])
    refresh_button.pack(side='left', padx=5)
    chart_button = tk.Button(button_frame, text="Show Pie Chart", command=lambda: generate_pie_chart(chart_frame))
    chart_button.pack(side='left', padx=5)
    close_chart_button = tk.Button(button_frame, text="Close Chart", command=lambda: close_chart(chart_frame))
    close_chart_button.pack(side='left', padx=5)
    delete_button = tk.Button(button_frame, text="Delete Selected", command=lambda: delete_investment(tree))
    delete_button.pack(side='left', padx=5)
    export_button = tk.Button(button_frame, text="Export to CSV", command=export_to_csv)
    export_button.pack(side='left', padx=5)

    # Update Profit/Loss Tab
    update_profit_loss_tab = ttk.Frame(notebook)
    notebook.add(update_profit_loss_tab, text='Update Profit/Loss')

    tk.Label(update_profit_loss_tab, text="Select Investment:").grid(row=0, column=0, padx=10, pady=10)
    global investment_combobox
    investment_combobox = ttk.Combobox(update_profit_loss_tab)
    investment_combobox.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(update_profit_loss_tab, text="Profit/Loss Amount:").grid(row=1, column=0, padx=10, pady=10)
    global profit_loss_entry
    profit_loss_entry = tk.Entry(update_profit_loss_tab)
    profit_loss_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(update_profit_loss_tab, text="Update Date (YYYY-MM-DD):").grid(row=2, column=0, padx=10, pady=10)
    global update_date_entry
    update_date_entry = tk.Entry(update_profit_loss_tab)
    update_date_entry.grid(row=2, column=1, padx=10, pady=10)

    update_investment_combobox()

    def on_tab_change(event):
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")
        if tab_text == "Update Profit/Loss":
            update_investment_combobox()

    notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    update_button = tk.Button(update_profit_loss_tab, text="Update Profit/Loss", command=update_profit_loss)
    update_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Analysis Tab
    analysis_tab = ttk.Frame(notebook)
    notebook.add(analysis_tab, text='Analysis')

    analysis_columns = ("ID", "Name", "Total Profit/Loss (base)", "Rate of Return (%)")
    analysis_tree = ttk.Treeview(analysis_tab, columns=analysis_columns, show="headings")
    for col in analysis_columns:
        analysis_tree.heading(col, text=col)
        analysis_tree.column(col, width=150)
    analysis_tree.pack(fill='both', expand=True, padx=10, pady=10)

    load_analysis(analysis_tree)

    analysis_button_frame = ttk.Frame(analysis_tab)
    analysis_button_frame.pack(pady=5)
    analysis_refresh_button = tk.Button(analysis_button_frame, text="Refresh Analysis", command=lambda: load_analysis(analysis_tree))
    analysis_refresh_button.pack(side='left', padx=5)

    return root

# --- Run the Application ---

if __name__ == "__main__":
    initialize_database()
    check_expired_investments()
    send_notification("Time to update your investments!")
    root = create_main_window()
    root.mainloop()