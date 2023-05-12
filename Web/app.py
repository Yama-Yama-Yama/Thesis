from fileinput import filename
from flask import Flask, render_template, request, redirect
import sqlite3
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from keras.models import load_model
from waitress import serve

app = Flask(__name__)
app.config['IMAGE_UPLOADS'] = './static/images'

model1 = None
model2 = None
filename = None
selectedDiagnosis = None


def prediction():
    global filename
    classes = {
        0: 'PNEUMONIA',
        1: 'NORMAL'
    }
    # Load the image and resize it
    image = cv2.imread(os.path.join(app.config['IMAGE_UPLOADS'], filename), cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, (224, 224))

    # Convert the resized image to a NumPy array and normalize it
    image_array = np.array(image)
    image_array = image_array[np.newaxis, ..., np.newaxis]
    image_array = image_array / 255.0

    pred = model1.predict(image_array)
    finalPred = pred

    if (pred > 0.4 and pred < 0.6):
        pred2 = model2.predict(image)
        finalPred = (pred + pred2) / 2
        print(finalPred)

    if finalPred > 0.6:
        x = 1
        value = finalPred[0].astype(float) * 100
    elif finalPred < 0.4:
        x = 0
        value = 100 - finalPred[0].astype(float) * 100
    else:
        return 'ERR'

    returnval = f'{classes[x]} Probability: {round(value[0], 2)} %', f'{classes[x][0]}{round(value[0]/100, 2)}'
    return returnval


def loadmodel():
    global model1
    global model2
    model1 = load_model('./Models/model20E91ALRRCHKPTES.h5')
    model2 = load_model('./Models/backup.h5')
    return


def get_db_connection():
    conn = sqlite3.connect('./database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_data(conn, record_id):
    data = conn.execute(
        f'SELECT pd.id, taj, first_name, middle_name, last_name, pdiag.result, pdiag.image_name, pdiag.id as did FROM Patient_Data as pd JOIN Patient_Diagnosis as pdiag on pd.id = pdiag.patient_id WHERE pd.id = {record_id}').fetchall()
    return data


def get_patient_data(conn, patient_id):
    cur = conn.cursor()
    patient = cur.execute(
        f'SELECT pd.id, first_name, last_name, middle_name, taj, birthday, country, city, post_code, street, phone, email, emergency_contact_email, emergency_contact_phone, emergency_contact_first_name, emergency_contact_middle_name, emergency_contact_last_name FROM Patient_Data AS pd INNER JOIN Patient_Address AS pa on pd.id = pa.patient_id INNER JOIN Patient_Contact AS pc on pd.id = pc.patient_id WHERE pd.id = {patient_id}').fetchone()
    conn.commit()
    return patient


def get_treatment_data(conn, record_id, selectedDiagnosis):
    cur = conn.cursor()
    diagnosis_id = None
    if (selectedDiagnosis is None):
        diagnosis_id = cur.execute(
            f"SELECT id FROM Patient_Diagnosis WHERE patient_id = {record_id} ORDER BY id DESC").fetchone()
        if (diagnosis_id is not None):
            diagnosis_id = int(diagnosis_id[0])
    else:
        diagnosis_id = selectedDiagnosis

    if (diagnosis_id is not None):
        data = conn.execute(
            f'SELECT * FROM Patient_Treatment WHERE diagnosis_id = {diagnosis_id}')
        conn.commit()
        return data
    return None


def insert_diagnoses(conn, task):
    sql = "INSERT INTO Patient_Diagnosis (result, image_name, patient_id) VALUES(?,?,?)"
    cur = conn.cursor()
    cur.execute(sql, (task[0], task[1], task[2]))
    conn.commit()


def update_patient_data(conn, task, record_id):
    cur = conn.cursor()

    sql1 = f"UPDATE Patient_Data SET birthday = '{task[10]}', taj = '{task[9]}', first_name = '{task[0]}', middle_name = '{task[1]}', last_name = '{task[2]}' WHERE id = {record_id}"
    sql2 = f"UPDATE Patient_Contact SET phone = '{task[4]}', email = '{task[3]}' WHERE patient_id = {record_id}"
    sql4 = f"UPDATE Patient_Contact SET emergency_contact_phone = '{task[12]}', emergency_contact_email = '{task[11]}', emergency_contact_first_name = '{task[13]}', emergency_contact_middle_name = '{task[14]}', emergency_contact_last_name = '{task[15]}' WHERE patient_id = {record_id}"
    sql3 = f"UPDATE Patient_Address SET country ='{task[5]}', post_code='{task[7]}', city='{task[6]}', street='{task[8]}' WHERE patient_id = '{record_id}'"
    cur.execute(sql1)
    cur.execute(sql2)
    cur.execute(sql3)
    cur.execute(sql4)
    conn.commit()


def insert_treatment(conn, task, patient_id, selectedDiagnosis):
    sql = "INSERT INTO Patient_Treatment (treatment, issued_by, diagnosis_id) VALUES(?,?,?)"
    cur = conn.cursor()
    diagnosis_id = None
    if (selectedDiagnosis is None):
        diagnosis_id = cur.execute(
            f"SELECT id FROM Patient_Diagnosis WHERE patient_id = {patient_id} ORDER BY id DESC").fetchone()
        if (diagnosis_id is not None):
            diagnosis_id = int(diagnosis_id[0])
    else:
        diagnosis_id = selectedDiagnosis

    cur.execute(sql, (task[0], task[1], diagnosis_id))
    conn.commit()


def insert_patient(conn, task):
    cur = conn.cursor()
    newId = cur.execute(f"SELECT MAX(id) FROM Patient_Data").fetchone()
    if (newId[0] is not None):
        newId = newId[0] + 1
    else:
        newId = 0
    sql1 = "INSERT INTO Patient_Data (birthday, taj, first_name, middle_name, last_name) VALUES(?,?,?,?,?)"
    sql2 = "INSERT INTO Patient_Contact (patient_id, phone, email) VALUES(?,?,?)"
    sql3 = "INSERT INTO Patient_Address (patient_id, country, post_code, city, street) VALUES(?,?,?,?,?)"
    cur.execute(sql1, (task[10], task[9], task[0], task[1], task[2]))
    cur.execute(sql2, (newId, task[4], task[3]))
    cur.execute(sql3, (newId, task[5], task[7], task[6], task[8]))
    conn.commit()


def remove_patient(conn, patient_id):
    cur = conn.cursor()
    diagnoses = cur.execute(
        f"SELECT id FROM Patient_Diagnosis WHERE patient_id = {patient_id}").fetchall()

    if (diagnoses is not None):
        for i in diagnoses:
            remove_diagnoses(conn, i[0])

    sql1 = f"DELETE FROM Patient_Address WHERE patient_id = {patient_id}"
    sql2 = f"DELETE FROM Patient_Contact WHERE patient_id = {patient_id}"
    sql3 = f"DELETE FROM Patient_Data WHERE id = {patient_id}"

    cur.execute(sql1)
    cur.execute(sql2)
    cur.execute(sql3)

    conn.commit()


def remove_treatment(conn, treatment_id):
    sql = f"DELETE FROM Patient_Treatment WHERE id = {treatment_id}"
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def remove_diagnoses(conn, diagnosis_id):
    cur = conn.cursor()
    treatments = cur.execute(
        f"SELECT id FROM Patient_Treatment WHERE diagnosis_id = {diagnosis_id}").fetchall()

    if (treatments is not None):
        for i in treatments:
            remove_treatment(conn, i[0])

    sql = f"DELETE FROM Patient_Diagnosis WHERE id = {diagnosis_id}"

    cur.execute(sql)
    conn.commit()


@ app.route("/")
@ app.route("/home")
def home():
    return render_template("home.html")


@ app.route("/patients", methods=["POST", "GET"])
def patients():
    conn = get_db_connection()
    with conn:
        data = conn.execute(
            "SELECT pd.id, first_name, last_name, middle_name, taj, birthday, pa.country, pa.city FROM Patient_Data AS pd INNER JOIN Patient_Address AS pa on pd.id = pa.patient_id").fetchall()
        if request.method == 'POST':
            if (request.form['submit_button'] == 'RemovePatient'):
                remove_patient(conn, request.form.get('id'))

            if (request.form['submit_button']) == 'AddNew':
                firstName = request.form['FirstNameText']
                middleName = request.form['MiddleNameText']
                lastName = request.form['LastNameText']
                email = request.form['EmailText']
                phone = request.form['MobileText']
                country = request.form['CountryText']
                city = request.form['CityText']
                postCode = request.form['PostText']
                street = request.form['StreetText']
                taj = request.form['TAJNumber']
                birthday = request.form['BirthdayText']
                insert_patient(conn, [firstName, middleName, lastName, email,
                                 phone, country, city, postCode, street, taj, birthday])

            #if (request.form['submit_button']) == 'EditExisting':
                # firstName = request.form['FirstNameText']
                # middleName = request.form['MiddleNameText']
                # lastName = request.form['LastNameText']
                # email = request.form['EmailText']
                # phone = request.form['MobileText']
                # country = request.form['CountryText']
                # city = request.form['CityText']
                # postCode = request.form['PostText']
                # street = request.form['StreetText']
                # taj = request.form['TAJNumber']
                # birthday = request.form['BirthdayText']

            data = conn.execute(
                "SELECT pd.id, first_name, last_name, middle_name, taj, birthday, pa.country, pa.city FROM Patient_Data AS pd INNER JOIN Patient_Address AS pa on pd.id = pa.patient_id").fetchall()
            return render_template("patients.html", data=data)
    return render_template("patients.html", data=data)


@ app.route("/choose", methods=["POST", "GET"])
def choose():
    conn = get_db_connection()
    data = conn.execute(
        "SELECT pd.id, first_name, last_name, middle_name, taj, birthday, pa.country, pa.city FROM Patient_Data AS pd INNER JOIN Patient_Address AS pa on pd.id = pa.patient_id").fetchall()
    conn.close()
    return render_template("choosePatient.html", data=data)


@ app.route("/predict", methods=["POST", "GET"])
@ app.route("/predict/<int:record_id>", methods=["POST", "GET"])
def predict(record_id):
    global filename
    global selectedDiagnosis
    conn = get_db_connection()
    data = get_data(conn, record_id)
    treatment_data = get_treatment_data(conn, record_id, selectedDiagnosis)

    if request.method == 'POST':
        if request.form['submit_button'] == 'Submit':
            image = request.files['file']
            if image.filename == '':
                print("File name is invalid")
                return redirect(request.url)

            filename = secure_filename(image.filename)
            if(filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))):
                basedir = os.path.abspath(os.path.dirname(__file__))
                image.save(os.path.join(
                    basedir, app.config["IMAGE_UPLOADS"], filename))

                data = get_data(conn, record_id)
                if (treatment_data is not None):
                    return render_template("predict.html", filename=filename, data=data, treatment_data=treatment_data, id=record_id)
                else:
                    return render_template("predict.html", filename=filename, data=data, id=record_id)

        if (request.form['submit_button']) == 'Predict':
            pred_value = prediction()
            insert_diagnoses(conn, (pred_value[1], filename, record_id))
            data = get_data(conn, record_id)
            if (treatment_data is not None):
                return render_template("predict.html", filename=filename, prediction=pred_value[0], data=data, treatment_data=treatment_data, id=record_id)
            else:
                return render_template("predict.html", filename=filename, prediction=pred_value[0], data=data, id=record_id)

        if (request.form['submit_button']) == 'Treatment':
            treatment = request.form['TreatmentText']
            issuedBy = request.form['IssuedBy']
            insert_treatment(conn, (treatment, issuedBy),
                            record_id, selectedDiagnosis)
            treatment_data = get_treatment_data(
                conn, record_id, selectedDiagnosis)
            if (treatment_data is not None):
                return render_template("predict.html", filename=filename, data=data, treatment_data=treatment_data, id=record_id)
            else:
                return render_template("predict.html", filename=filename, data=data, id=record_id)

        if (request.form['submit_button'] == 'remove_treatment'):
            remove_treatment(conn, request.form.get('id'))
            treatment_data = get_treatment_data(
                conn, record_id, selectedDiagnosis)
            if (treatment_data is not None):
                return render_template("predict.html", filename=filename, data=data, treatment_data=treatment_data, id=record_id)
            else:
                return render_template("predict.html", filename=filename, data=data, id=record_id)

        if (request.form['submit_button'] == 'SelectDiagnosis'):
            selectedDiagnosis = request.form.get('did')
            treatment_data = get_treatment_data(
                conn, record_id, selectedDiagnosis)
            if (treatment_data is not None):
                return render_template("predict.html", filename=filename, data=data, treatment_data=treatment_data, id=record_id)
            else:
                return render_template("predict.html", filename=filename, data=data, id=record_id)

    if (treatment_data is not None):
        return render_template("predict.html", data=data, treatment_data=treatment_data, id=record_id)
    return render_template("predict.html", data=data, id=record_id)

@ app.route("/editPatient", methods=["POST", "GET"])
@ app.route("/editPatient/<int:record_id>", methods=["POST", "GET"])
def edit_patient(record_id):
    global selectedDiagnosis
    conn = get_db_connection()
    patient_data = get_patient_data(conn, record_id)
    treatment_data = get_treatment_data(conn, record_id, selectedDiagnosis)
    data = get_data(conn, record_id)
    with conn:
        if request.method == 'POST':
            if (request.form['submit_button']) == 'Treatment':
                treatment = request.form['TreatmentText']
                issuedBy = request.form['IssuedBy']
                insert_treatment(conn, (treatment, issuedBy),
                                record_id, selectedDiagnosis)
                treatment_data = get_treatment_data(
                    conn, record_id, selectedDiagnosis)

            if (request.form['submit_button'] == 'remove_diagnoses'):
                remove_diagnoses(conn, request.form.get('did'))
                treatment_data = get_treatment_data(
                    conn, record_id, selectedDiagnosis)
                data = get_data(conn, record_id)

            if (request.form['submit_button'] == 'remove_treatment'):
                remove_treatment(conn, request.form.get('id'))
                treatment_data = get_treatment_data(
                    conn, record_id, selectedDiagnosis)

            if (request.form['submit_button'] == 'SelectDiagnosis'):
                selectedDiagnosis = request.form.get('did')
                treatment_data = get_treatment_data(
                    conn, record_id, selectedDiagnosis)

            if (request.form['submit_button'] == 'update_patient_data'):
                firstName = request.form['FirstNameText']
                middleName = request.form['MiddleNameText']
                lastName = request.form['LastNameText']
                email = request.form['EmailText']
                phone = request.form['MobileText']
                country = request.form['CountryText']
                city = request.form['CityText']
                postCode = request.form['PostText']
                street = request.form['StreetText']
                taj = request.form['TAJNumber']
                birthday = request.form['BirthdayText']
                eContactEmail = request.form['EmergencyEmailText']
                eContactPhone = request.form['EmergencyMobileText']
                eContactFirstName = request.form['EmergencyFirstNameText']
                eContactMiddleName = request.form['EmergencyMiddleNameText']
                eContactLastName = request.form['EmergencyLastNameText']

                update_patient_data(conn, [firstName, middleName, lastName, email,
                                         phone, country, city, postCode, street, taj, birthday, eContactEmail, eContactPhone, eContactFirstName, eContactMiddleName, eContactLastName], record_id)
                patient_data = get_patient_data(conn, record_id)

            if (treatment_data is not None):
                return render_template("patientEdit.html", data=data, patient_data=patient_data, id=record_id, treatment_data=treatment_data)
            return render_template("patientEdit.html", data=data, patient_data=patient_data, id=record_id)

    if (treatment_data is not None):
        return render_template("patientEdit.html", data=data, patient_data=patient_data, id=record_id, treatment_data=treatment_data)
    return render_template("patientEdit.html", data=data, patient_data=patient_data, id=record_id)


if __name__ == '__main__':
    loadmodel()
    #app.run(debug=True)
    serve(app, host='0.0.0.0', port=50100, threads=2)
