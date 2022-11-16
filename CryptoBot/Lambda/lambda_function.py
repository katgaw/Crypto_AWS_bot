### Required Libraries ###
from datetime import datetime
from dateutil.relativedelta import relativedelta

### Functionality Helper Functions ###
def parse_int(n):
    """
    Securely converts a non-integer value to integer.
    """
    try:
        return int(n)
    except ValueError:
        return float("nan")


def build_validation_result(is_valid, violated_slot, message_content):
    """
    Define a result message structured as Lex response.
    """
    if message_content is None:
        return {"isValid": is_valid, "violatedSlot": violated_slot}

    return {
        "isValid": is_valid,
        "violatedSlot": violated_slot,
        "message": {"contentType": "PlainText", "content": message_content},
    }

def parse_float(n):
    """
    Securely converts a non-numeric value to float.
    """
    try:
        return float(n)
    except ValueError:
        return float("nan")

def validate_data(age, investmentAmount, risk_level, intent_request):
    """
    Validates the data provided by the user.
    """

    # Validate that the user is over 21 years old
    if age is not None:
        age = parse_float(age)
        if age<=0:
            return build_validation_result(
                False,
                "age",
                "You should be at least 0 years old to use this service, "
                "please provide a different age.",
            )

    # Validate the investment amount, it should be > 0
    if investmentAmount is not None:
        investmentAmount = parse_float(
            investmentAmount
        )  # Since parameters are strings it's important to cast values
        if investmentAmount < 1000:
            return build_validation_result(
                False,
                "investmentAmount",
                "The amount to convert should be greater or equal to 1000, "
                "please provide a correct amount.",
            )
    if risk_level is not None:
        risk_level=str(risk_level)
        if risk_level=='None':
            return build_validation_result(
                    False,
                    "riskLevel",
                    "Your portfolio should be 100% bonds (AGG), 0% equities (SPY)"
                )

        if risk_level=='Low':
            return build_validation_result(
                    False,
                    "riskLevel",
                    f'You should invest in USD coin. You can expect cumulative return of ${round(investmentAmount*0.000004,0)}. In the past 6 months, you would have cumulatively made ${round(investmentAmount*0.000002,0)}.'
                )

        if risk_level=='Medium':
            return build_validation_result(
                    False,
                    "riskLevel",
                    f'You should invest in Bitcoin. You can expect cumulative return of ${round(investmentAmount*41.452569,0)}. In the past 6 months you would have cumulatively made ${round(investmentAmount*44.217867,0)}.'
                )

        if risk_level=='High':
            return build_validation_result(
                    False,
                    "riskLevel",
                    f'You should invest in Wrapped-Bitcoin. You can expect cumulative return of ${round(investmentAmount*41.674941,0)}. In the past 6 months you would have cumulatively made ${round(investmentAmount*44.199972,0)}.'
                )
    # A True results is returned if the variables are valid
    return build_validation_result(True, None, None)


### Dialog Actions Helper Functions ###
def get_slots(intent_request):
    """
    Fetch all the slots and their values from the current intent.
    """
    return intent_request["currentIntent"]["slots"]


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    """
    Defines an elicit slot type response.
    """

    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "ElicitSlot",
            "intentName": intent_name,
            "slots": slots,
            "slotToElicit": slot_to_elicit,
            "message": message,
        },
    }


def delegate(session_attributes, slots):
    """
    Defines a delegate slot type response.
    """

    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {"type": "Delegate", "slots": slots},
    }


def close(session_attributes, fulfillment_state, message):
    """
    Defines a close slot type response.
    """

    response = {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": fulfillment_state,
            "message": message,
        },
    }

    return response


"""
Step 3: Enhance the Robo Advisor with an Amazon Lambda Function

"""


### Intents Handlers ###
def recommend_portfolio(intent_request):
    """
    Performs dialog management and fulfillment for recommending a portfolio.
    """

    first_name = get_slots(intent_request)["firstName"]
    age = get_slots(intent_request)["age"]
    investmentAmount = get_slots(intent_request)["investmentAmount"]
    risk_level = get_slots(intent_request)["riskLevel"]
    source = intent_request["invocationSource"]

    if source == "DialogCodeHook":
        # This code performs basic validation on the supplied input slots.

        # Gets all the slots
        slots = get_slots(intent_request)

        # Validates user's input using the validate_data function
        validation_result = validate_data(age, investmentAmount, risk_level, intent_request)

        # If the data provided by the user is not valid,
        # the elicitSlot dialog action is used to re-prompt for the first violation detected.
        if not validation_result["isValid"]:
            slots[validation_result["violatedSlot"]] = None  # Cleans invalid slot

            # Returns an elicitSlot dialog to request new data for the invalid slot
            return elicit_slot(
                intent_request["sessionAttributes"],
                intent_request["currentIntent"]["name"],
                slots,
                validation_result["violatedSlot"],
                validation_result["message"],
            )

        # Fetch current session attributes
        output_session_attributes = intent_request["sessionAttributes"]

        # Once all slots are valid, a delegate dialog is returned to Lex to choose the next course of action.
        return delegate(output_session_attributes, get_slots(intent_request))

    # Return a message with result.
    
    return close(
        intent_request["sessionAttributes"],
        "Fulfilled",
        {
            "contentType": "PlainText",
            "content": """Thank you for your information"""
        },
    )


### Intents Dispatcher ###
def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    intent_name = intent_request["currentIntent"]["name"]

    # Dispatch to bot's intent handlers
    if intent_name == "recommendPortfolio":
        return recommend_portfolio(intent_request)

    raise Exception("Intent with name " + intent_name + " not supported")


### Main Handler ###
def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """

    return dispatch(event)
