from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import date, datetime
from itertools import groupby

app = Flask(__name__)
DATABASE = 'expenses.db'


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create the expenses table if it doesn't exist."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def format_date_label(date_str):
    """Convert a date string to a friendly label like 'Today', 'Yesterday', or 'March 28'."""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return date_str
    today = date.today()
    from datetime import timedelta
    if d == today:
        return "Today, " + d.strftime('%B %d')
    elif d == today - timedelta(days=1):
        return "Yesterday, " + d.strftime('%B %d')
    else:
        return d.strftime('%B %d, %Y')


# Category icon mapping
CATEGORY_ICONS = {
    'Food': 'bi-cart',
    'Transport': 'bi-bus-front',
    'Shopping': 'bi-bag',
    'Bills': 'bi-receipt',
    'Entertainment': 'bi-film',
    'Health': 'bi-heart-pulse',
    'Education': 'bi-book',
    'Salary': 'bi-briefcase',
    'Freelance': 'bi-laptop',
    'Investment': 'bi-graph-up-arrow',
    'Rent': 'bi-house',
    'Other': 'bi-three-dots',
}

CATEGORY_COLORS = {
    'Food': '#ff6b6b',
    'Transport': '#51cf66',
    'Shopping': '#cc5de8',
    'Bills': '#ff922b',
    'Entertainment': '#9775fa',
    'Health': '#f06595',
    'Education': '#20c997',
    'Salary': '#339af0',
    'Freelance': '#fcc419',
    'Investment': '#38d9a9',
    'Rent': '#e8590c',
    'Other': '#868e96',
}


@app.route('/')
def index():
    """Home page — dashboard view."""
    conn = get_db()

    # Get filter from query params
    filter_type = request.args.get('filter', 'all')  # all, income, expense

    if filter_type == 'income':
        expenses = conn.execute(
            "SELECT * FROM expenses WHERE type='income' ORDER BY date DESC, id DESC"
        ).fetchall()
    elif filter_type == 'expense':
        expenses = conn.execute(
            "SELECT * FROM expenses WHERE type='expense' ORDER BY date DESC, id DESC"
        ).fetchall()
    else:
        expenses = conn.execute(
            'SELECT * FROM expenses ORDER BY date DESC, id DESC'
        ).fetchall()

    # Calculate totals using SUM()
    result = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) AS total_income, "
        "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS total_spent "
        "FROM expenses"
    ).fetchone()

    total_income = result['total_income']
    total_spent = result['total_spent']
    balance = total_income - total_spent

    # Category breakdown for budget chart
    categories = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE type='expense' "
        "GROUP BY category ORDER BY total DESC"
    ).fetchall()

    # Convert Row objects to dicts before closing connection
    expenses = [dict(row) for row in expenses]
    categories = [dict(row) for row in categories]

    conn.close()

    # Group transactions by date
    grouped = []
    for date_key, group_items in groupby(expenses, key=lambda x: x['date']):
        grouped.append({
            'label': format_date_label(date_key),
            'entries': list(group_items)
        })

    return render_template('index.html',
                           grouped=grouped,
                           total_income=total_income,
                           total_spent=total_spent,
                           balance=balance,
                           filter_type=filter_type,
                           categories=categories,
                           category_icons=CATEGORY_ICONS,
                           category_colors=CATEGORY_COLORS)


@app.route('/add', methods=['POST'])
def add():
    """Insert a new expense/income entry."""
    title = request.form['title']
    amount = float(request.form['amount'])
    category = request.form['category']
    entry_type = request.form['type']
    entry_date = request.form['date']

    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (title, amount, category, type, date) VALUES (?, ?, ?, ?, ?)',
        (title, amount, category, entry_type, entry_date)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit an existing entry."""
    conn = get_db()

    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        category = request.form['category']
        entry_type = request.form['type']
        entry_date = request.form['date']

        conn.execute(
            'UPDATE expenses SET title=?, amount=?, category=?, type=?, date=? WHERE id=?',
            (title, amount, category, entry_type, entry_date, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    expense = conn.execute('SELECT * FROM expenses WHERE id=?', (id,)).fetchone()
    conn.close()

    if expense is None:
        return redirect(url_for('index'))

    return render_template('edit.html', expense=expense,
                           category_icons=CATEGORY_ICONS,
                           category_colors=CATEGORY_COLORS)


@app.route('/delete/<int:id>')
def delete(id):
    """Delete an entry and redirect home."""
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
