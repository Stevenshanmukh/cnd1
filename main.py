import os
from flask import Flask, redirect, request, send_file, render_template_string
from google.cloud import datastore, storage

# Initialize clients
datastore_client = datastore.Client()
storage_client = storage.Client()

# Define the Cloud Storage bucket
BUCKET_NAME = "imagecnd1"

app = Flask(__name__)

@app.route('/')
def index():
    files = get_list_of_files()
    
    index_html = """
    <h1>Upload and View Images</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
      <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="form_file" accept="image/jpeg"/>
      </div>
      <div>
        <button>Submit</button>
      </div>
    </form>
    <ul>"""
    
    for file in files:
        index_html += f"<li><a href='{file}'>{file}</a></li>"
    
    index_html += "</ul>"
    
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']
    blob = storage_client.bucket(BUCKET_NAME).blob(file.filename)
    blob.upload_from_file(file)

    add_db_entry({"name": file.filename, "url": blob.public_url})
    
    return redirect("/")

def get_list_of_files():
    """Retrieve file URLs from Cloud Datastore"""
    query = datastore_client.query(kind="photos")
    return [photo["url"] for photo in query.fetch()]

def add_db_entry(entry):
    """Store file metadata in Cloud Datastore"""
    entity = datastore.Entity(key=datastore_client.key('photos'))
    entity.update(entry)
    datastore_client.put(entity)

if __name__ == '__main__':
    app.run(debug=True)
