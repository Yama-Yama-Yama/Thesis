DROP TABLE IF EXISTS Patient_Data;

CREATE TABLE Patient_Data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    birthday DATETIME NOT NULL,
    taj VARCHAR(100) NOT NULL UNIQUE,
    first_name VARCHAR(75) NOT NULL,
    middle_name VARCHAR(75),
    last_name VARCHAR(75) NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS Patient_Contact;

CREATE TABLE Patient_Contact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id int,
    email varchar(200),
    phone varchar(50),
    emergency_contact_phone varchar(50),
    emergency_contact_email varchar(200),
    emergency_contact_first_name varchar(75),
    emergency_contact_last_name varchar(75),
    emergency_contact_middle_name varchar(75),
    FOREIGN KEY(patient_id) REFERENCES Patient_Data(id)
);

DROP TABLE IF EXISTS Patient_Address;

CREATE TABLE Patient_Address (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id int,
    country VARCHAR(75),
    post_code VARCHAR(75),
    city VARCHAR(75),
    street VARCHAR(75),
    FOREIGN KEY(patient_id) REFERENCES Patient_Data(id)
);

DROP TABLE IF EXISTS Patient_Diagnosis;

CREATE TABLE Patient_Diagnosis(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id int,
    result VARCHAR(75),
    image_name VARCHAR(250),
    FOREIGN KEY(patient_id) REFERENCES Patient_Data(id)
);

DROP TABLE IF EXISTS Patient_Treatment;

CREATE TABLE Patient_Treatment(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnosis_id int,
    treatment TEXT,
    issued_by varchar(75),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(diagnosis_id) REFERENCES Patient_Diagnosis(id)
);