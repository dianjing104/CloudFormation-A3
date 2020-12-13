import math
import dateutil.parser
import os
import time
import logging
import boto3
import json

import requests
from requests_aws4auth import AWS4Auth


region = 'us-east-1' # e.g. us-east-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-photo-storage-3gex4uqz77gf2abn5bvis25ilm.us-east-1.es.amazonaws.com' # the Amazon ES domain, with https://
index = 'photos'
type = '_search'
url = host + '/' + index + '/' + type + '/'

headers = { "Content-Type": "application/json" }

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except Exception:
        return False


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def validate_searchkey(keyword_1,keyword_2):
    keywords = ['tree', 'person', 'dog', 'glass','milk','coffee cup', 'cup', 'alcohol','human','finger','face', 'wine glass', 'goblet']
    if keyword_1 is not None and keyword_1.lower() not in keywords:
        return build_validation_result(False,
                                       'searchkeyone',
                                       'Sorry, we only have {}, would you like a different type of photo?  '.format(keywords))

    if keyword_2 is not None and keyword_2.lower() not in keywords:
            
        return build_validation_result(False,
                                        'searchkeytwo',
                                        'Sorry, we only have {}, would you like a different type of photo?  '.format(keywords))

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """
    
    


def search_intent(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """
    
    keyword_1 = get_slots(intent_request)["searchkeyone"]
    keyword_2 = get_slots(intent_request)["searchkeytwo"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_searchkey(keyword_1,keyword_2)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
            
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}


        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    
    # sqs = boto3.resource('sqs')

    # queue = sqs.get_queue_by_name(QueueName='restaurants_request')
    # msg = {"location":location, "cuisine": cuisine,"numberofpeople":num_people, "phone": phone}
    # response = queue.send_message(MessageBody=json.dumps(msg))
    # print(response)
    
    print(keyword_1)
    print(keyword_2)
    print('start searching')
    
    if keyword_2 is not None:
        query ={
            "query":{
                "bool":{
                    "must":[
                        {"term": {"labels": keyword_1}},
                        {"term": {"labels": keyword_2}}]
                        }
                    },
        "size": 1000 #number of rows you want to get in the result
                }
    else:
        query ={
            "query":{
                "match": {
                    "labels" : keyword_1
                    }
                },
        "size": 1000 #number of rows you want to get in the result
    }
    
    r = requests.get(url, auth=awsauth, json=query, headers=headers)

    results = json.loads(r.text)
    print(results)
    
    ## to do
    n_hits = int(results['hits']['total']['value'])
    print(n_hits)
    
    photo_object = ''
    
    if(len(results['hits']['hits'])==0):
        print("No matching photo Found")
        return close(intent_request['sessionAttributes'],
                    'Fulfilled',
                    {'contentType': 'PlainText',
                    'content': 'None'})       
    else:
        for hit in results['hits']['hits']: #loop the data
            photo_object +=(hit['_source']['objectKey'])
            photo_object += ' '
            print("photo Data\n",hit)
             # use hit['_source']['<required_filedname>'] to retreive the required feild data from your lambda
            #print("User Name-->",hit['_source']['id']) 


    #return photo index to frontend
    print(photo_object)
    #return photo_idx
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': photo_object
                  })


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'SearchIntent':
        return search_intent(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    
    
    
    print('event is following:')
    print(event)

    return dispatch(event)



