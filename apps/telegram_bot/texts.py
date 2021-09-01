START_TEXT = """
Hello {}, welcome to plutus bot!\n
to creating an alert for your preferred asset and strategy, tap on `Create Alert` button and enter your alert key.
"""

CREATE_ALERT_BUTTON = "🔔 Create Alert"
STOP_ALERT_BUTTON = "🔕 Stop Alert"
ALERT_LIST_BUTTON = "📜 Alerts List"

STOP_TEXT = """
👋 We will look forward to see you again {}.
"""

CREATE_ALERT_TEXT = """
Please enter your alert key in order to set alert for your asset.
"""

ALERT_CREATED_TEXT = """
✅ Great! your alert has been set.
"""

ALERT_NOT_EXISTS_TEXT = """
No alert has been found with this alert key.
"""

ALERT_LIST = """
{% for alert in logs %}
Alert datetime: {{alert.created_time | date:'Y-m-d H:i'}}
{{ alert.log }}
Key: {{ alert.strategy_alert.alert_key }}
 {% if not forloop.last %}
 _________________________________
 {% endif %} 
{% endfor %}
"""
NO_ALERT_EXISTS = """
You have no logs or alerts
"""
STOP_ALERT = """
Please enter your alert key in order to stop the alert.
"""

STOP_ALERT_DONE = """
❌ Your alert has been deactivated.
"""

WRONG_COMMAND = """
🚫 Invalid Command
"""

ERROR_TEXT = """
⭕️ Couldn't complete the process. please try again!
"""
