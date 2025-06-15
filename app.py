import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "https://wealthsync-frontend2.onrender.com",
    "http://localhost:3000"
]}})

# In-memory database for budget history
budget_history = []

# Mock economic data for all states and Union Territories in India
economic_data = {
    "andhra pradesh": {"inflation": 5.2, "cost_of_living_index": 48},
    "arunachal pradesh": {"inflation": 4.9, "cost_of_living_index": 45},
    "assam": {"inflation": 5.0, "cost_of_living_index": 42},
    "bihar": {"inflation": 4.7, "cost_of_living_index": 40},
    "chhattisgarh": {"inflation": 4.8, "cost_of_living_index": 43},
    "goa": {"inflation": 5.8, "cost_of_living_index": 60},
    "gujarat": {"inflation": 5.3, "cost_of_living_index": 50},
    "haryana": {"inflation": 5.5, "cost_of_living_index": 55},
    "himachal pradesh": {"inflation": 4.9, "cost_of_living_index": 47},
    "jharkhand": {"inflation": 4.6, "cost_of_living_index": 41},
    "karnataka": {"inflation": 5.7, "cost_of_living_index": 58},
    "kerala": {"inflation": 5.4, "cost_of_living_index": 52},
    "madhya pradesh": {"inflation": 4.8, "cost_of_living_index": 44},
    "maharashtra": {"inflation": 6.0, "cost_of_living_index": 65},
    "manipur": {"inflation": 5.1, "cost_of_living_index": 46},
    "meghalaya": {"inflation": 4.9, "cost_of_living_index": 45},
    "mizoram": {"inflation": 5.0, "cost_of_living_index": 47},
    "nagaland": {"inflation": 5.2, "cost_of_living_index": 46},
    "odisha": {"inflation": 4.7, "cost_of_living_index": 42},
    "punjab": {"inflation": 5.4, "cost_of_living_index": 53},
    "rajasthan": {"inflation": 4.8, "cost_of_living_index": 45},
    "sikkim": {"inflation": 5.0, "cost_of_living_index": 48},
    "tamil nadu": {"inflation": 5.6, "cost_of_living_index": 55},
    "telangana": {"inflation": 5.5, "cost_of_living_index": 54},
    "tripura": {"inflation": 4.9, "cost_of_living_index": 43},
    "uttar pradesh": {"inflation": 4.7, "cost_of_living_index": 41},
    "uttarakhand": {"inflation": 4.9, "cost_of_living_index": 46},
    "west bengal": {"inflation": 5.3, "cost_of_living_index": 50},
    # Union Territories
    "andaman and nicobar islands": {"inflation": 5.5, "cost_of_living_index": 58},
    "chandigarh": {"inflation": 5.6, "cost_of_living_index": 60},
    "dadra and nagar haveli and daman and diu": {"inflation": 5.2, "cost_of_living_index": 50},
    "delhi": {"inflation": 5.9, "cost_of_living_index": 62},
    "jammu and kashmir": {"inflation": 5.1, "cost_of_living_index": 48},
    "ladakh": {"inflation": 5.0, "cost_of_living_index": 47},
    "lakshadweep": {"inflation": 5.4, "cost_of_living_index": 55},
    "puducherry": {"inflation": 5.3, "cost_of_living_index": 52},
    # Default for unknown locations
    "default": {"inflation": 5.0, "cost_of_living_index": 50}
}

# Tier classification for major cities (simplified)
tiered_cities = {
    # Tier 1 Cities
    "mumbai": {"state": "maharashtra", "tier": 1},
    "delhi": {"state": "delhi", "tier": 1},
    "bangalore": {"state": "karnataka", "tier": 1},
    "hyderabad": {"state": "telangana", "tier": 1},
    "chennai": {"state": "tamil nadu", "tier": 1},
    "kolkata": {"state": "west bengal", "tier": 1},
    "ahmedabad": {"state": "gujarat", "tier": 1},
    "pune": {"state": "maharashtra", "tier": 1},
    # Tier 2 Cities
    "jaipur": {"state": "rajasthan", "tier": 2},
    "lucknow": {"state": "uttar pradesh", "tier": 2},
    "kanpur": {"state": "uttar pradesh", "tier": 2},
    "nagpur": {"state": "maharashtra", "tier": 2},
    "indore": {"state": "madhya pradesh", "tier": 2},
    "thiruvananthapuram": {"state": "kerala", "tier": 2},
    "bhopal": {"state": "madhya pradesh", "tier": 2},
    "visakhapatnam": {"state": "andhra pradesh", "tier": 2},
    "patna": {"state": "bihar", "tier": 2},
    "vadodara": {"state": "gujarat", "tier": 2},
    "coimbatore": {"state": "tamil nadu", "tier": 2}
}

# Minimum recommended percentages of income for each Maslow level
maslow_minimums = {
    "physiological": 0.40,  # 40% of income for food, shelter, etc.
    "safety": 0.20,        # 20% for safety (e.g., insurance, savings)
    "social": 0.10,        # 10% for social activities
    "esteem": 0.05,        # 5% for esteem (e.g., education)
    "self_actualization": 0.05  # 5% for self-actualization
}

# Endpoint to get list of cities
@app.route('/api/cities', methods=['GET'])
def get_cities():
    cities = [
        {"name": city.capitalize(), "state": info["state"].capitalize()}
        for city, info in tiered_cities.items()
    ]
    return jsonify(cities)

@app.route('/api/budget', methods=['POST'])
def calculate_budget():
    data = request.get_json()
    email = data.get('email')
    income = float(data.get('income'))
    expenses = float(data.get('expenses'))
    savings_goal = float(data.get('savings_goal'))
    location = data.get('location', '').lower()
    expense_categories = data.get('expense_categories', {})

    # Extract categorized expenses
    physiological = expense_categories.get('physiological', 0)
    safety = expense_categories.get('safety', 0)
    social = expense_categories.get('social', 0)
    esteem = expense_categories.get('esteem', 0)
    self_actualization = expense_categories.get('self_actualization', 0)

    # Determine if the location is a tiered city, else use state-level data
    city_info = tiered_cities.get(location, None)
    if city_info:
        state = city_info["state"]
        tier = city_info["tier"]
    else:
        # If not a tiered city, assume it's a state or use default
        state = location if location in economic_data else "default"
        tier = 3  # Treat as Tier 3 (no adjustment)

    # Get base economic data for the state
    location_data = economic_data.get(state, economic_data["default"])
    inflation = location_data["inflation"]
    cost_of_living_index = location_data["cost_of_living_index"]

    # Adjust economic data based on city tier
    if tier == 1:
        inflation += 1.0  # +1% inflation for Tier 1 cities
        cost_of_living_index *= 1.20  # +20% cost of living
    elif tier == 2:
        inflation += 0.5  # +0.5% inflation for Tier 2 cities
        cost_of_living_index *= 1.10  # +10% cost of living

    # Calculate savings
    savings = income - expenses

    # Adjust recommended savings based on inflation
    recommended_savings = savings_goal * (1 + inflation / 100)

    # Adjust expenses based on cost of living
    expense_ratio = cost_of_living_index / 50
    adjusted_expenses = expenses * expense_ratio
    adjusted_savings = income - adjusted_expenses

    # Generate a message based on savings
    if savings >= savings_goal:
        message = "Great job! You're meeting your savings goal."
    else:
        message = "You need to save more to meet your goal. Consider reducing expenses."

    # Check Maslow's Hierarchy of Needs
    recommendations = []
    # Physiological needs
    min_physiological = maslow_minimums["physiological"] * income
    if physiological < min_physiological:
        recommendations.append(f"Your physiological expenses (₹{physiological}) are below the recommended minimum (₹{min_physiological:.2f}). Reallocate funds from higher-level needs (e.g., social, self-actualization) to cover basic needs like food and shelter.")
    # Safety needs (only check if physiological needs are met)
    if physiological >= min_physiological:
        min_safety = maslow_minimums["safety"] * income
        if safety < min_safety:
            recommendations.append(f"Your safety expenses (₹{safety}) are below the recommended minimum (₹{min_safety:.2f}). Ensure you allocate enough for insurance, emergency savings, or financial security.")
    # Higher-level needs (only recommend if lower needs are met)
    if physiological >= min_physiological and safety >= min_safety:
        min_social = maslow_minimums["social"] * income
        if social < min_social:
            recommendations.append(f"Your social expenses (₹{social}) are below the recommended minimum (₹{min_social:.2f}). Consider allocating more for social activities to improve your relationships and well-being.")
        min_esteem = maslow_minimums["esteem"] * income
        if esteem < min_esteem:
            recommendations.append(f"Your esteem expenses (₹{esteem}) are below the recommended minimum (₹{min_esteem:.2f}). Allocate some funds for education or personal achievements.")
        min_self_actualization = maslow_minimums["self_actualization"] * income
        if self_actualization > 0 and (physiological < min_physiological or safety < min_safety):
            recommendations.append(f"You’re spending ₹{self_actualization} on self-actualization (e.g., hobbies), but your basic needs aren’t fully met. Reallocate these funds to physiological or safety needs.")

    # Other recommendations
    if expenses > 0.7 * income:
        recommendations.append("Your expenses are high. Try cutting down on non-essential spending.")
    if savings < 0:
        recommendations.append("You're spending more than you earn. Create a stricter budget.")
    if cost_of_living_index > 60:
        recommendations.append(f"Living in {location.capitalize()} is expensive. Consider relocating or finding cheaper alternatives for housing and daily expenses.")
    elif cost_of_living_index < 45:
        recommendations.append(f"Living in {location.capitalize()} is relatively affordable. You can allocate more towards savings or investments.")
    recommendations.append("Consider investing in low-risk options like fixed deposits.")

    # Store the budget entry in history
    budget_entry = {
        'id': len(budget_history) + 1,
        'email': email,
        'income': income,
        'expenses': expenses,
        'savings': savings,
        'savings_goal': savings_goal,
        'recommended_savings': recommended_savings,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    budget_history.append(budget_entry)

    return jsonify({
        'savings': savings,
        'adjusted_savings': adjusted_savings,
        'recommended_savings': recommended_savings,
        'inflation': inflation,
        'cost_of_living_index': cost_of_living_index,
        'message': message,
        'recommendations': recommendations,
        'expense_categories': {
            'physiological': physiological,
            'safety': safety,
            'social': social,
            'esteem': esteem,
            'self_actualization': self_actualization
        }
    })

@app.route('/api/budget/history', methods=['POST'])
def get_budget_history():
    data = request.get_json()
    email = data.get('email')
    user_history = [entry for entry in budget_history if entry['email'] == email]
    return jsonify(user_history)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
