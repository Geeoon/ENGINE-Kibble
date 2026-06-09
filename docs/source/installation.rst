Installation and Setup
======================

Prerequisites
-------------

- Python 3.x
- MongoDB
- pip

Setup Steps
-----------

1. Clone the Repository

.. code-block:: bash

   git clone https://github.com/Geeoon/ENGINE-Kibble.git
   cd ENGINE-Kibble

2. Create and activate a virtual environment:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate

3. Install Dependencies

.. code-block:: bash

   pip install -r requirements.txt

4. Set required environment variables:

   .. code-block:: bash

      export EMAIL_PASSWD=your_email_password


5. Start MongoDB and verify the connection settings.

6. Run the System

.. code-block:: bash

   python main.py