import os
import traceback
from flask import Flask, redirect, request, render_template_string
from google.cloud import datastore, storage
from werkzeug.utils import secure_filename
from google.cloud.exceptions import GoogleCloudError

# Google Cloud configurations
PROJECT_ID = "slagadapati-cnd-p1"
BUCKET_NAME = "cloudnativenew"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# Initialize Flask app
app = Flask(__name__)

# Initialize Google Cloud clients
datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client()

# Ensure local storage directory exists
LOCAL_STORAGE_DIR = "files"
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Render file upload form and list uploaded images by filenames with images displayed."""
    files = get_list_of_files()

    index_html = """
    <h1>Upload and View Images</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
      <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="form_file" accept="image/jpeg,image/png"/>
      </div>
      <div>
        <button>Submit</button>
      </div>
    </form>
    <ul>"""
    
    for file in files:
        # Generate the public URL for the image
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file}"
        index_html += f"""
        <li>
          <strong>{file}</strong><br>
          <img src="{public_url}" alt="{file}" width="200" /><br>
        </li>
        """
    
    index_html += "</ul>"
    
    return index_html

@app.route("/upload", methods=["POST"])
def upload():
    """Handle file upload and save to Cloud Storage."""
    try:
        file = request.files.get("form_file")

        if not file or file.filename == "" or not allowed_file(file.filename):
            print("No file uploaded or unsupported file type.")
            return redirect("/")

        # Secure filename and prepare paths
        filename = secure_filename(file.filename)
        local_file_path = os.path.join(LOCAL_STORAGE_DIR, filename)

        # Save locally
        file.save(local_file_path)
        print(f"File saved locally: {local_file_path}")

        # Upload to Cloud Storage
        blob = storage_client.bucket(BUCKET_NAME).blob(filename)
        try:
            blob.upload_from_filename(local_file_path)
            print(f"File uploaded to GCS: {blob.public_url}")
        except GoogleCloudError as gcs_error:
            print(f"Error uploading file to GCS: {gcs_error}")
            traceback.print_exc()
            return render_template_string("<h1>Error occurred during upload to Cloud Storage. Please try again.</h1>")

        # Add metadata to Datastore
        add_db_entry({"name": filename, "url": blob.public_url})

        # Make the file publicly accessible
        blob.make_public()
        print(f"File made public: {blob.public_url}")

        # Remove local file after upload
        os.remove(local_file_path)
        print(f"Local file {local_file_path} removed after upload.")

    except Exception as e:
        print(f"Error during upload: {e}")
        traceback.print_exc()
        return render_template_string("<h1>Error occurred during upload. Please try again.</h1>")

    return redirect("/")

def get_list_of_files():
    """Retrieve image filenames from Cloud Datastore."""
    try:
        query = datastore_client.query(kind="photos")
        return [photo["name"] for photo in query.fetch()]  # Return the 'name' field
    except Exception as e:
        print(f"Error retrieving files: {e}")
        return []

def add_db_entry(entry):
    """Store file metadata in Cloud Datastore."""
    try:
        entity = datastore.Entity(key=datastore_client.key("photos"))
        entity.update(entry)
        datastore_client.put(entity)
        print("Datastore entry added:", entry)
    except Exception as e:
        print(f"Error storing in Datastore: {e}")

if __name__ == "__main__":
    app.run(debug=True)
