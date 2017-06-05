from oauth2client.service_account import ServiceAccountCredentials

step_username = ''
step_password = ''
district_name_full = ''
save_path = ''

gcloud_keyfile = ''
gcloud_project_name = ''
gcs_bucket_name = ''
gcloud_credentials = ServiceAccountCredentials.from_json_keyfile_name(gcloud_keyfile)

CONFIG = {
        'step_username': step_username,
        'step_password': step_password,
        'district_name_full': district_name_full,        
        'save_path': save_path,
        'gcloud_credentials': gcloud_credentials,
        'gcloud_project_name': gcloud_project_name,
        'gcs_bucket_name': gcs_bucket_name
    }
