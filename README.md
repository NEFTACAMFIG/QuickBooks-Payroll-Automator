# QuickBooks-Payroll-Automator: Excel API Integration

pip install pandas requests openpyxl
    ```

## ⚙️ Installation & Usage

1.¡Claro que sí! Una versión en inglés es fundamental si quieres que tu repositorio tenga un alcance global y se vea más profesional para empresas internacionales o reclutadores técnicos.

Aquí tienes la traducción adaptada:

***

# QuickBooks Check Automator

![QuickBooks API](https://img.shields.io/badge/API-QuickBooks-green) ![Python](https://img.shields.io/badge/Python-3.x-blue) ![Pandas](https://img.shields.io/badge/Library-Pandas-orange)

**QuickBooks Check Automator** is an automation solution designed to streamline the payroll and project payment process. The program extracts data from attendance reports (Excel), processes it, and leverages the **QuickBooks API** to automatically generate and upload checks, eliminating human error and saving hours of manual data entry.

## 🚀 Project Overview

This system acts as a smart bridge between external data files and the QuickBooks accounting platform. Its modular architecture allows for the validation of internal company identifiers before proceeding with the financial creation of documents.

## 🛠️ Program Structure

The project is divided into 4 specialized modules:

### 1. `id_employee`
Handles personnel synchronization.
* **Function:** Sends GET requests to the QuickBooks API.
* **Objective:** Maps employee names to their internal **QuickBooks System ID** to ensure each check is assigned to the correct entity.

### 2. `id_project`
Manages cost centers or project entities.
* **Function:** Queries the API to retrieve internal **Project/Customer IDs**.
* **Importance:** Ensures every payment is properly categorized under a specific project in QuickBooks, enabling accurate job costing and profitability reports.

### 3. `Connecteam` (Data Processor)
The core business logic and data cleaning engine.
* **Function:** Ingests the Excel document (based on Connecteam reports or similar platforms), cleans the information, and consolidates the data.
* **Output:** Generates an optimized **Pandas DataFrame** including:
    * Worker and Project IDs.
    * Project Name.
    * Calculated hours worked.
    * Total amount to be paid.

### 4. `Quickbooks` (Final Uploader)
The execution module that interacts with the accounting ledger.
* **Function:** Reads the processed DataFrame and performs POST requests to the QuickBooks API.
* **Result:** Individually creates checks with all required metadata and uploads them to the QuickBooks platform in real-time.

---

## 📋 Prerequisites

Before running the program, ensure you have:
1.  **Intuit Developer Credentials:** Client ID and Client Secret from the [Intuit Developer Portal](https://developer.intuit.com/).
2.  **Access Token:** Active OAuth 2.0 configuration.
3.  **Python Libraries:**
    ```bash
    pip install pandas requests openpyxl
    ```

## 🛡️ Security
This program handles sensitive financial information. It is highly recommended to:
* Never upload your `.env` file or access tokens to the repository (already included in `.gitignore`).
* Use the **QuickBooks Sandbox** environment for testing before moving to production.

---
**Developed to optimize business accounting through intelligent automation.**
