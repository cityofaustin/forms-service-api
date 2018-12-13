# Flask
from flask import Flask, flash, request, render_template, \
                    redirect, url_for, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# File Management
import os, io, base64, boto3, datetime, time, calendar, requests
from PIL import Image

# Random hash generation
import uuid, hashlib

# Knack integrator
import knackpy, json



















#  dP""b8  dP"Yb  88b 88 888888 88  dP""b8
# dP   `" dP   Yb 88Yb88 88__   88 dP   `"
# Yb      Yb   dP 88 Y88 88""   88 Yb  "88
#  YboodP  YbodP  88  Y8 88     88  YboodP

#
# Configuration & Environment Variables
#

UPLOAD_FOLDER = '/tmp'
DEPLOYMENT_MODE           = os.environ.get("DEPLOYMENT_MODE")
ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])


KNACK_APPLICATION_ID      = os.environ.get("KNACK_APPLICATION_ID")
KNACK_API_KEY             = os.environ.get("KNACK_API_KEY")
KNACK_OBJECT_ID           = os.environ.get("KNACK_OBJECT_ID")
KNACK_API_ENDPOINT_FILE_UPLOADS="https://api.knack.com/v1/applications/" + KNACK_APPLICATION_ID + "/assets/file/upload"

S3_BUCKET                 = os.environ.get("AWS_BUCKET_NAME")
S3_LOCATION               = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

LOG_TABLE                 = "police-monitor-records"#os.environ['LOG_TABLE']


app = Flask(__name__)
CORS(app) # Get rid of me!!!!
# https://github.com/corydolphin/flask-cors

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DEPLOYMENT_MODE'] = DEPLOYMENT_MODE
app.config['S3_BUCKET'] = S3_BUCKET
app.config['S3_LOCATION'] = S3_LOCATION
app.config['LOG_TABLE'] = LOG_TABLE

if(DEPLOYMENT_MODE=="local"):
    S3_KEY                    = os.environ.get("AWS_ACCESS_KEY_ID")
    S3_SECRET                 = os.environ.get("AWS_SECRET_ACCESS_KEY")
    app.config['S3_KEY']      = S3_KEY
    app.config['S3_SECRET']   = S3_SECRET
    s3 = boto3.client("s3", aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
else:
    s3 = boto3.client("s3")

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')




























#8  88 888888 88     88""Yb 888888 88""Yb .dP"Y8
#8  88 88__   88     88__dP 88__   88__dP `Ybo."
#88888 88""   88  .o 88"""  88""   88"Yb  o.`Y8b
#8  88 888888 88ood8 88     888888 88  Yb 8bodP'

#
# Helper Functions
#
def build_response(inputDict):
    return jsonify(inputDict), inputDict["status_code"]

def filename_timestamp():
  now = datetime.datetime.now()
  return now.strftime("%m%d%Y")

def getCurrentDateTime():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower()

def allowed_file(filename):
    return '.' in filename and \
            get_file_extension(filename) in ALLOWED_EXTENSIONS

def is_image(filename):
    return get_file_extension(filename) in ALLOWED_IMAGE_EXTENSIONS

def is_json(inputText):
    try:
        json_object = json.loads(inputText)
        # The JSON is good
        return True
    except:
        # The JSON test is bad
        return False

def load_map(file_path):
    return json.load(open(file_path))

def generate_random_hash():
    rand_uuid_str = "{0}".format(uuid.uuid1()).encode()
    return hashlib.sha256(rand_uuid_str).hexdigest()

def generate_random_filename(filename):
  timestamp = filename_timestamp()
  original_extension = get_file_extension(filename)
  output_hash = generate_random_hash()
  return "{0}_{1}.{2}".format(timestamp, output_hash, original_extension)

def get_knack_object(tablename):
    knack_objects = load_map('./knackmaps/knack_objects.json')
    return knack_objects[tablename]

def build_knack_item_raw(inputJson, map):
    # Copy record map, we do not want it modified
    rawRecord = map.copy()

    # Convert inputJson to string (if it isn't)
    if(isinstance(inputJson, str)):
        jsonObject = json.loads(inputJson)
    else:
        jsonObject = inputJson

    # For each key,val in jsonObject
    for key, val in jsonObject.items():
        try:
            rawRecord[key] = val
        except:
            print("Invalid Key: " + key)

    return rawRecord

def build_knack_item(inputJson, map, record):
    # Copy record map, we do not want it modified
    knackRecord = record.copy()

    # Convert inputJson to string (if it isn't)
    if(isinstance(inputJson, str)):
        jsonObject = json.loads(inputJson)
    else:
        jsonObject = inputJson

    # For each key,val in jsonObject
    for key, val in jsonObject.items():
        try:
            knackRecord[map[key]] = val
        except:
            print("Invalid Key: " + key)

    return knackRecord

def knack_create_record(record, table='complaints'):
    response = knackpy.record(
        record,
        obj_key = get_knack_object(table),
        app_id  = KNACK_APPLICATION_ID,
        api_key = KNACK_API_KEY,
        method='create'
    )

    return response["id"], response




def create_dynamodb_record(inputJson, type='record', knack_record_id=''):
    if(isinstance(inputJson, str) == False):
        jsonString = json.dumps(inputJson)
    else:
        jsonString = inputJson

    random_hash = generate_random_hash()
    resp = dynamodb_client.put_item(
        TableName=LOG_TABLE,
        Item={
            'entryId': {'S': random_hash }, # A random identifier
            'timestamp': {'N': str(int(time.time())) }, # Epoch Time
            'dateCreated': {'S': getCurrentDateTime() }, # Epoch Time
            'type': {'S': type }, # Epoch Time
            'data': { 'S': jsonString },
            'knackRecordId': {'S': knack_record_id }
        }
    )
    return random_hash, resp

def knack_upload_image(filepath):
    # First try uploading the image and parse the response
    try:
        headers = {'x-knack-rest-api-key': KNACK_API_KEY }
        multiple_files = [('files', open(filepath, 'rb'))]
        return requests.post(KNACK_API_ENDPOINT_FILE_UPLOADS, headers=headers, files=multiple_files)
    # We've failed along the way...
    except:
        print("It should have never reached this point!")
        return "error"


def upload_file_to_s3(file, bucket_name, acl="public-read"):
    """
    Docs: http://boto3.readthedocs.io/en/latest/guide/s3.html
    """
    newFilename = generate_random_filename(file.filename)

    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            newFilename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )

    except Exception as e:
        print("Something Happened: ", e)
        return e

    return "{}{}".format(app.config["S3_LOCATION"], newFilename)


#
# Routes
#

@app.route('/')
def index():
    return "Hello, world!", 200
























#8  dP 88b 88    db     dP""b8 88  dP     88""Yb 888888  dP""b8  dP"Yb  88""Yb 8888b.  .dP"Y8
#8odP  88Yb88   dPYb   dP   `" 88odP      88__dP 88__   dP   `" dP   Yb 88__dP  8I  Yb `Ybo."
#8"Yb  88 Y88  dP__Yb  Yb      88"Yb      88"Yb  88""   Yb      Yb   dP 88"Yb   8I  dY o.`Y8b
#8  Yb 88  Y8 dP""""Yb  YboodP 88  Yb     88  Yb 888888  YboodP  YbodP  88  Yb 8888Y"  8bodP'



@app.route('/knack/getrecord/<string:record_id>', methods=['GET'])
def get_record(record_id):
    print("Record: " + record_id)
    dynamodb_response = dynamodb_client.get_item(
        TableName=LOG_TABLE,
        Key={
            'entryId': { 'S': str(record_id) }
        }
    )

    item = dynamodb_response.get('Item')
    print(item)

    if not item:
        return jsonify({'error': 'User does not exist'}), 404

    return jsonify({
        'entryId': item.get('entryId').get('S'),
        'timestamp': item.get('timestamp').get('N'),
        'type': item.get('type').get('S'),
        'data': item.get('data').get('S')
    }), 200




@app.route('/knack/submit', methods=['POST'])
def knack_testrelationships():
    jsonInputData = None

    try:
        jsonInputData = request.get_json()
    except:
        return "Invalid JSON request", 403

    knack_officer_map = load_map("./knackmaps/knack_officer_map.json")
    knack_officer_record = load_map("./knackmaps/knack_officer_record.json")

    knack_witness_map = load_map("./knackmaps/knack_witness_map.json")
    knack_witness_record = load_map("./knackmaps/knack_witness_record.json")

    knack_evidence_map = load_map("./knackmaps/knack_evidence_map.json")
    knack_evidence_record = load_map("./knackmaps/knack_evidence_record.json")

    knack_complaint_map = load_map("./knackmaps/knack_complaint_map.json")
    knack_complaint_record = load_map("./knackmaps/knack_complaint_record.json")

    knack_compliment_map = load_map("./knackmaps/knack_compliment_map.json")
    knack_compliment_record = load_map("./knackmaps/knack_compliment_record.json")

    officersId = []
    witnessesId = []
    evidenceFileIds = []

    #
    # First create the officers' records (if any provided)
    #
    try:
        for officer in jsonInputData["officers"]:
            knack_record = build_knack_item(officer, knack_officer_map, knack_officer_record)
            entry_id, response = knack_create_record(knack_record, table="officers")
            officersId.append(entry_id)
            print("New Officer creted: " +  entry_id)
    except Exception as e:
        print("Error while creating officer records: " + e.message)

    try:
        for witness in jsonInputData["witnesses"]:
            knack_record = build_knack_item(witness, knack_witness_map, knack_witness_record)
            entry_id, response = knack_create_record(knack_record, table="witnesses")
            witnessesId.append(entry_id)
            print("New witness creted: " +  entry_id)
    except Exception as e:
        print("Error while creating witness records: " + e.message)



    #
    #  Now the evidence records
    #

    try:
        for knackFileId in jsonInputData["evidence"]:
            new_evidence_data = knack_evidence_map.copy()
            new_evidence_data["evidenceFile"] = knackFileId
            new_evidence_data["evidenceName"] = "Knack Attachment Id: {0}".format(knackFileId)
            new_evidence_data["evidenceUploadDate"] = getCurrentDateTime()
            new_evidence_record = build_knack_item(new_evidence_data, knack_evidence_map, knack_evidence_record)
            entry_id, response = knack_create_record(new_evidence_record, table="evidence")
            evidenceFileIds.append(entry_id)
            print("New Evidence File Creted: " +  entry_id)
    except Exception as e:
        print("Error while creating evidence records: " + e.message)

    #
    # We now build the full record
    #
    knack_record = build_knack_item(jsonInputData, knack_complaint_map, knack_complaint_record)

    # We begin associating officers and evidence records to the full record.
    # Get the knack key for the officers & witnesses column & assign the value to that key
    knack_record[knack_complaint_map["officers"]] = officersId
    knack_record[knack_complaint_map["witnesses"]] = witnessesId
    knack_record[knack_complaint_map["evidence"]] = evidenceFileIds

    knack_record_raw = json.dumps(jsonInputData)
    knack_record_plain = json.dumps(knack_record)

    knack_record_id, response = knack_create_record(knack_record)
    dyn_record_id, dynamodb_response = create_dynamodb_record(knack_record_raw, type='complaint', knack_record_id=knack_record_id)
    print("New Record Created! knack_record_id: {0}, dynamo_record_id: {1}".format(knack_record_id, dyn_record_id))

    response = {}
    return jsonify(response), 200



























#88888 88 88     888888     88   88 88""Yb 88      dP"Yb     db    8888b.  .dP"Y8
#8__   88 88     88__       88   88 88__dP 88     dP   Yb   dPYb    8I  Yb `Ybo."
#8""   88 88  .o 88""       Y8   8P 88"""  88  .o Yb   dP  dP__Yb   8I  dY o.`Y8b
#8     88 88ood8 888888     `YbodP' 88     88ood8  YbodP  dP""""Yb 8888Y"  8bodP'



#
# First method: local file, then to knack api.
#

@app.route('/upload-knack-form', methods=['GET'])
def upload_file_knack():
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action='/upload-knack' method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/upload-knack', methods=['GET', 'POST'])
def upload_file():

    response = {
        "status": "error",
        "status_code": 403,
        "knack-file-id": "",
        "message": "Failed to upload file."
    }

    # Check if the method is post
    if request.method == 'POST':

        # check if the post request has the file part
        if 'file' not in request.files:
            response["message"] = "No file part"
            return build_response(response)

        # Gather file from request
        file = request.files['file']

        # if user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            response["message"] = "No selected file"
            return build_response(response)

        # If the file has a permitted extension
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            new_filename = generate_random_filename(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

            # We are going to try to save the file first, then upload to knack
            try:
                file.save(file_path)
                r = knack_upload_image(file_path)

                # If the response is a JSON file, then we are OK
                if(is_json(r.text)):
                    file_record = r.json()
                    response["status"] = "success"
                    response["status_code"] = 200
                    response["knack-file-record"] = file_record["id"]
                    response["message"] = file_record["public_url"]
                    dyn_rid, dyn_resp = create_dynamodb_record(json.dumps(response), type='attachment', knack_record_id=file_record["id"])
                    print("New Image uploaded: " + file_record["id"])
                else:
                    print("We have a problem: " + r.text)
                    response["message"] = "Error: " + r.text


            except Exception as e:
                response["message"] = "Error while uploading: " + str(e)

            return build_response(response)

    # Not a POST request, redirect to form
    else:
        response["message"] = "Not a POST request"

    return build_response(response)

@app.route('/uploads-knack/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




#
# Second Method: S3 File Uploader, then add url to knack image field.
#

@app.route("/upload-s3", methods=["GET"])
def upload_file_s3_form():
    return render_template('index.html', url=url_for('upload_file_s3')), 200

@app.route("/upload-s3", methods=["POST"])
def upload_file_s3():

	# A. Check if there
    if "user_file" not in request.files:
        return "No user_file key in request.files"

	# B. Instantiate file handle
    file    = request.files["user_file"]

    """
        These attributes are also available
        file.filename               # The actual name of the file
        file.content_type
        file.content_length
        file.mimetype
    """

	# C. Check filename is not empty
    if file.filename == "":
        return "Please select a file"

	# D. if there is a file and is allowed
    if file and allowed_file(file.filename):
        file.filename = secure_filename(file.filename)
        output   	  = upload_file_to_s3(file, app.config["S3_BUCKET"])
        return str(output), 200

    else:
        return redirect("/")


# We only need this for local development.
if __name__ == '__main__':
    app.run()