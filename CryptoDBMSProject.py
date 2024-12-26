from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import pyqtSignal
import sys
import pyodbc

server = 'INSPIRON15\\SQLSERVER1'
database = 'Project'
use_windows_authentication = True 
username = 'your_username'
password = 'your_password'

if use_windows_authentication:
    connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
else:
    connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

class UI(QtWidgets.QMainWindow):
    def __init__(self):
        super(UI, self).__init__()
        uic.loadUi('Login.ui', self)

        # Connection buttons
        self.SignUP.clicked.connect(self.openSignup)  
        self.Login.clicked.connect(self.handleLogin)
        self.Admin.clicked.connect(self.openAdminLogin)
        self.superAdmin.clicked.connect(self.openSuperAdminLogin)

    def openSuperAdminLogin(self):
        # Open SuperAdminLogin
        self.hide()
        self.super_admin_login_window = SuperAdminLogin()
        self.super_admin_login_window.show()
        self.super_admin_login_window.backLogin.connect(self.show)

    def openAdminLogin(self):
        # Open AdminLogin
        self.hide() # Hide the login window
        self.admin_login_window = AdminLogin()
        self.admin_login_window.show()
        self.admin_login_window.backLogin.connect(self.show) 

    def handleLogin(self):
        wallet_id = self.WalletID.text()
        password = self.Password.text()

        # Check Input
        if not wallet_id or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both WalletID and Password.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check credentials
        cursor.execute("SELECT WalletID FROM Users WHERE WalletID = ? AND Password = ?", (wallet_id, password))
        result = cursor.fetchone()

        if result:
            QMessageBox.information(self, "Login Successful", f"Welcome, Wallet ID: {wallet_id}")
            # Open Wallet
            self.wallet_window = WalletWindow(wallet_id)
            self.wallet_window.show()
            self.close() 
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid WalletID or Password.")

        cursor.close()
        connection.close()

    def openSignup(self):
        # Open SignUp
        self.hide()  # Hide the login window
        self.sign_up_window = SignUpWindow()
        self.sign_up_window.show()
        self.sign_up_window.backLogin.connect(self.show) 

class WalletWindow(QtWidgets.QMainWindow):

    def __init__(self, wallet_id):
        super(WalletWindow, self).__init__()
        uic.loadUi('BalAndWallet.ui', self)
        self.wallet_id = wallet_id
        self.walletData()

        # Set read-only fields
        self.CurrentBal.setDisabled(True)
        self.TotalCoinValue.setDisabled(True)

        # Connection buttons 
        self.Back.clicked.connect(self.goBack)
        self.CoinInfo.clicked.connect(self.coinList)
        self.Deposit.clicked.connect(lambda: self.openBalanceChange("Deposit"))
        self.Withdraw.clicked.connect(lambda: self.openBalanceChange("Withdraw"))
        self.Buy.clicked.connect(self.openBuyOrder)
        self.Sell.clicked.connect(self.openSellOrder)
        self.Trade.clicked.connect(self.openTrade)
        self.Request.clicked.connect(self.openRequestCheck)

    def openRequestCheck(self):
        # Open the RequestCheck
        request_check_window = RequestCheck(self.wallet_id)
        if request_check_window.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.walletData()

    def openTrade(self):
        # Open TradeWindow
        trade_window = TradeWindow(self.wallet_id)
        if trade_window.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.walletData()

    def openSellOrder(self):
        # Open SellOrder
        sell_order = SellOrder(self.wallet_id)
        if sell_order.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.walletData()

    def openBuyOrder(self):
        # Open BuyOrder
        buy_order = BuyOrder(self.wallet_id)
        if buy_order.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.walletData()

    def openBalanceChange(self, action_type):
        # Open DepositWithdraw
        change_bal = ChangeBalance(self.wallet_id, action_type)
        if change_bal.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.walletData()

    def coinList(self):
        # Open CoinList
        self.coin_list = CoinList()
        self.coin_list.exec()

    def walletData(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Set balance
        cursor.execute("SELECT Balance FROM Users WHERE WalletID = ?", (self.wallet_id,))
        balance = cursor.fetchone()[0]
        self.CurrentBal.setText(f"${float(balance):.2f}")

        # Set coins and their total value
        cursor.execute("""
            SELECT Coin.CoinID, Coin.CoinName, Wallet.Quantity, Coin.Price
            FROM Wallet
            JOIN Coin ON Wallet.CoinID = Coin.CoinID
            WHERE WalletID = ?
        """, (self.wallet_id,))
        
        total_value = 0.0
        self.WalletCoinList.setRowCount(0)

        for row_index, (coin_id, coin_name, quantity, price) in enumerate(cursor.fetchall()):
            quantity = float(quantity)
            price = float(price)
            coin_value = quantity * price
            total_value += coin_value

            self.WalletCoinList.insertRow(row_index)
            self.WalletCoinList.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.WalletCoinList.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))
            self.WalletCoinList.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"{quantity:.2f}"))

        self.TotalCoinValue.setText(f"${total_value:.2f}")

        cursor.close()
        connection.close()

    def goBack(self):
        self.close()

class RequestCheck(QtWidgets.QDialog):
    def __init__(self, wallet_id):
        super(RequestCheck, self).__init__()
        uic.loadUi('requestcheck.ui', self) 
        self.wallet_id = wallet_id 

        # Connect the buttons to their functions
        self.Accept.clicked.connect(self.acceptRequest)
        self.Reject.clicked.connect(self.rejectRequest)
        self.Check.clicked.connect(self.checkRequest)

        self.populateRequests()

    def populateRequests(self):
        # Fetch the trades where WalletID2 matches the current wallet_id and the status is 'Pending'
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT TradeID
            FROM Trades
            WHERE WalletID2 = ? AND Status = 'Pending'
        """, (self.wallet_id,))

        trades = cursor.fetchall()

        self.Requests.clear()

        if not trades:
            QMessageBox.information(self, "No Pending Trades", "No pending trades found for this wallet.")
        else:
            # Populate the ComboBox with TradeIDs
            for trade in trades:
                self.Requests.addItem(f"{trade[0]}") 

        cursor.close()
        connection.close()

    def acceptRequest(self):
        selected_request = self.Requests.currentText()
        if selected_request:
            trade_id = int(selected_request)

            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE Trades
                SET Status = 'Accepted'
                WHERE TradeID = ?
            """, (trade_id,))

            connection.commit()
            cursor.close()
            connection.close()

            QMessageBox.information(self, "Request Accepted", f"Request {trade_id} has been accepted.")
            
            self.populateRequests()

        else:
            QMessageBox.warning(self, "No Request Selected", "Please select a request to accept.")

    def rejectRequest(self):
        selected_request = self.Requests.currentText()
        if selected_request:
            trade_id = int(selected_request)

            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            cursor.execute("""
                SELECT EmployeeID
                FROM Trades
                WHERE TradeID = ?
            """, (trade_id,))
            employee_id = cursor.fetchone()

            if employee_id:
                # Get the EmployeeID from the result
                employee_id = employee_id[0]

                # Update the trade status to 'Rejected'
                cursor.execute("""
                    UPDATE Trades
                    SET Status = 'Rejected'
                    WHERE TradeID = ?
                """, (trade_id,))

                # Update the NumberOfRequests for the employee
                cursor.execute("""
                    UPDATE Employee
                    SET NumberOfRequests = NumberOfRequests - 1
                    WHERE EmployeeID = ?
                """, (employee_id,))

                connection.commit()
                cursor.close()
                connection.close()

                QMessageBox.information(self, "Request Rejected", f"Request {trade_id} has been rejected.")

                self.populateRequests()
            else:
                QMessageBox.warning(self, "Employee Not Found", "No employee found for this trade.")
        else:
            QMessageBox.warning(self, "No Request Selected", "Please select a request to reject.")

    def checkRequest(self):
        selected_request = self.Requests.currentText()
        if selected_request:
            trade_id = int(selected_request) 

            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            cursor.execute("""
                SELECT 
                    T.TradeID, T.WalletID1, T.WalletID2, 
                    C1.CoinName AS CoinName1, C2.CoinName AS CoinName2, 
                    T.Quantity1, T.Quantity2, T.Status, T.Date, T.EmployeeID
                FROM Trades T
                JOIN Coin C1 ON T.CoinID1 = C1.CoinID
                JOIN Coin C2 ON T.CoinID2 = C2.CoinID
                WHERE T.TradeID = ?
            """, (trade_id,))

            trade_details = cursor.fetchone()

            if trade_details:
                # Show trade details in a message box
                trade_info = f"""
                    Trade ID: {trade_details[0]}
                    Request From WalletID: {trade_details[1]}
                    Trade Their  {trade_details[5]:.2f} {trade_details[3]}
                    For Your {trade_details[6]:.2f} {trade_details[4]}.
                """

                QMessageBox.information(self, "Trade Details", trade_info)
            else:
                QMessageBox.warning(self, "Trade Not Found", f"No details found for Trade ID {trade_id}.")

            cursor.close()
            connection.close()
        else:
            QMessageBox.warning(self, "No Request Selected", "Please select a request to check.")

class TradeWindow(QtWidgets.QDialog):

    def __init__(self, wallet_id):
        super(TradeWindow, self).__init__()
        uic.loadUi('MakeTrade.ui', self)

        self.wallet_id = wallet_id
        self.populateCoins()
        self.populateWalletCoins()

        # Connect buttons
        self.Trade.clicked.connect(self.processTrade)

    def populateCoins(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get available coins
        cursor.execute("SELECT CoinID, CoinName, Price FROM Coin")
        coins = cursor.fetchall()

        self.Coins.setRowCount(len(coins))
        self.Coins.setColumnCount(2)
        self.Coins.setHorizontalHeaderLabels(["Coin ID", "Coin Name"])

        for row_index, (coin_id, coin_name, _) in enumerate(coins):
            self.Coins.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.Coins.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))

        cursor.close()
        connection.close()

    def populateWalletCoins(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get the coins in the user's wallet
        cursor.execute("""
            SELECT Coin.CoinID, Coin.CoinName, Wallet.Quantity
            FROM Wallet
            JOIN Coin ON Wallet.CoinID = Coin.CoinID
            WHERE WalletID = ?
        """, (self.wallet_id,))
        wallet_coins = cursor.fetchall()

        self.WalletCoinList.setRowCount(len(wallet_coins))
        self.WalletCoinList.setColumnCount(3)
        self.WalletCoinList.setHorizontalHeaderLabels(["Coin ID", "Coin Name", "Quantity"])

        for row_index, (coin_id, coin_name, quantity) in enumerate(wallet_coins):
            self.WalletCoinList.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.WalletCoinList.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))
            self.WalletCoinList.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"{quantity:.2f}"))

        cursor.close()
        connection.close()

    def processTrade(self):
        selected_row_1 = self.WalletCoinList.currentRow()
        selected_row_2 = self.Coins.currentRow()

        if selected_row_1 == -1 or selected_row_2 == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a coin from both Wallet and available Coins.")
            return

        coin_id_1 = int(self.WalletCoinList.item(selected_row_1, 0).text())

        quantity_1_text = self.Quantity.text()
        try:
            quantity_1 = float(quantity_1_text)
            if quantity_1 <= 0 or round(quantity_1, 2) != quantity_1:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity with up to two decimal places.")
            return

        coin_id_2 = int(self.Coins.item(selected_row_2, 0).text())

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute("SELECT Price FROM Coin WHERE CoinID = ?", (coin_id_1,))
        price_1 = float(cursor.fetchone()[0]) 

        cursor.execute("SELECT Price FROM Coin WHERE CoinID = ?", (coin_id_2,))
        price_2 = float(cursor.fetchone()[0]) 


        # Calculate quantity for CoinID2 
        quantity_2 = (price_1 * quantity_1) / price_2

        wallet_id_2 = int(self.WalletID.text())

        # Check if wallet_id_1 exists and its status is not "Frozen"
        cursor.execute("SELECT Type FROM Users WHERE WalletID = ?", (self.wallet_id,))
        user_1 = cursor.fetchone()

        user_1_status = user_1[0]
        if user_1_status == "Frozen":
            QMessageBox.warning(self, f"Wallet ID {self.wallet_id} is Frozen", "Your account is frozen and cannot trade.")
            cursor.close()
            connection.close()
            return

        # Check if wallet_id_2 exsists
        cursor.execute("SELECT COUNT(*) FROM Users WHERE WalletID = ?", (wallet_id_2,))
        user_exists = cursor.fetchone()[0]

        if user_exists == 0:
            QMessageBox.warning(self, "Invalid Wallet ID", f"Wallet ID {wallet_id_2} does not exist in the system.")
            cursor.close()
            connection.close()
            return
        
        # Check if wallet_id_2 status is not "Frozen"
        cursor.execute("SELECT Type FROM Users WHERE WalletID = ?", (wallet_id_2,))
        user_2 = cursor.fetchone()

        user_2_status = user_2[0]
        if user_2_status == "Frozen":
            QMessageBox.warning(self, f"Wallet ID {wallet_id_2} is Frozen", "The other user's account is frozen and cannot trade.")
            cursor.close()
            connection.close()
            return

        # Find employee with the least requests
        cursor.execute("SELECT TOP 1 EmployeeID FROM Employee ORDER BY NumberOfRequests ASC")
        employee = cursor.fetchone()
        employee_id = employee[0]

        # Insert trade into Trades table
        cursor.execute("""
            INSERT INTO Trades (WalletID1, WalletID2, CoinID1, CoinID2, Quantity1, Quantity2, EmployeeID, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (self.wallet_id, wallet_id_2, coin_id_1, coin_id_2, quantity_1, quantity_2, employee_id))

        # Update NumberOfRequests
        cursor.execute("""
            UPDATE Employee SET NumberOfRequests = NumberOfRequests + 1 WHERE EmployeeID = ?
        """, (employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Trade Initiated", "Your trade has been initiated successfully.")
        self.accept()

class SignUpWindow(QtWidgets.QMainWindow):
    # Creates signal to go back, more efficient than closing and reopening windows
    backLogin = pyqtSignal() 

    def __init__(self):
        super(SignUpWindow, self).__init__()
        uic.loadUi('SignUp.ui', self)

        # Connection Buttons 
        self.SignUp.clicked.connect(self.signUp)
        self.Back.clicked.connect(self.goBack)

    def signUp(self):
        # Get user inputs from line edits
        password = self.Password.text()
        first_name = self.First.text()
        last_name = self.Last.text()
        email = self.Email.text()
        phone_no = self.Phone.text()
        address = self.Address.text()

        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address containing '@' and '.com'")
            return

        if not self.is_valid_phone(phone_no):
            QMessageBox.warning(self, "Invalid Phone Number", "Phone number must be at least 7 digits and numeric.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Create new user
        insert_query = """
        INSERT INTO Users (Password, FirstName, LastName, Email, PhoneNumber, Address, Type)
        VALUES (?, ?, ?, ?, ?, ?, 'Active')
        """

        cursor.execute(insert_query, (password, first_name, last_name, email, phone_no, address))
        connection.commit()

        # Check for duplicate walletid using unique email.
        cursor.execute("SELECT WalletID FROM Users WHERE Email = ?", (email,))
        walletID = cursor.fetchone()[0]  

        # Confirmation message
        QMessageBox.information(self, "Sign-Up Successful", f" Your Wallet ID is: {walletID}")

        cursor.close()
        connection.close()

        # Clear line edits
        self.Password.clear()
        self.First.clear()
        self.Last.clear()
        self.Email.clear()
        self.Phone.clear()
        self.Address.clear()
    
    def is_valid_email(self, email):
        return '@' in email and '.com' in email   

    def is_valid_phone(self, phone):
        return phone.isdigit() and len(phone) >= 7

    def goBack(self):
        # Uses the signal to open login and close current window
        self.backLogin.emit()
        self.close()

class CoinList(QtWidgets.QDialog):
    def __init__(self):
        super(CoinList, self).__init__()
        uic.loadUi('CoinList.ui', self)

        # Connection button
        self.Back.clicked.connect(self.close)

        # Set CoinTable with coins from database
        self.loadCoin()

    def loadCoin(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute("SELECT CoinID, CoinName, Price FROM Coin")
        coins = cursor.fetchall()
        
        # Set the tablewidget for coins
        self.CoinTable.setRowCount(len(coins))
        self.CoinTable.setColumnCount(3)
        self.CoinTable.setHorizontalHeaderLabels(["ID", "Coin Name", "Coin Value"])

        # Populate the table with coins
        for row_index, (coin_id, coin_name, price) in enumerate(coins):
            self.CoinTable.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.CoinTable.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))
            self.CoinTable.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"${price:.2f}"))

        cursor.close()
        connection.close()

class AdminLogin(QtWidgets.QMainWindow):
    backLogin = pyqtSignal()

    def __init__(self):
        super(AdminLogin, self).__init__()
        uic.loadUi('AdminLogin.ui', self) 

        # Connection Buttons
        self.Login.clicked.connect(self.handleAdminLogin)
        self.Back.clicked.connect(self.goBack)

    def handleAdminLogin(self):
        employee_id = self.WalletID.text()
        password = self.Password.text()

        # Check Input
        if not employee_id or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both EmployeeID and Password.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Check Credentials.
        cursor.execute("SELECT EmployeeID FROM Employee WHERE EmployeeID = ? AND Password = ?", (employee_id, password))
        result = cursor.fetchone()

        if result:
            QMessageBox.information(self, "Login Successful", f"Welcome, Admin ID: {employee_id}")
            self.WalletID.clear()
            self.Password.clear()
            # Open Admin
            self.admin_window = AdminWindow(self, employee_id)  
            self.admin_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid EmployeeID or Password.")

        cursor.close()
        connection.close()

    def goBack(self):
        self.backLogin.emit()
        self.close()

class AdminWindow(QtWidgets.QMainWindow):
    def __init__(self, admin_login_window, employee_id):
        super(AdminWindow, self).__init__()
        uic.loadUi('Admin.ui', self)

        # Store references
        self.admin_login_window = admin_login_window
        self.employee_id = employee_id

        # Populate dropdown with pending orders
        self.populateRequests()
        self.populateTradeRequests()

        # Connection buttons
        self.Back.clicked.connect(self.goBack)

        self.Check.clicked.connect(self.openOrderCheck)
        self.Accept.clicked.connect(self.acceptOrder)
        self.Reject.clicked.connect(self.rejectOrder)

        self.TradeAccept.clicked.connect(self.acceptTrade)
        self.TradeReject.clicked.connect(self.rejectTrade)
        self.TradeCheck.clicked.connect(self.openTradeCheck)

        self.Freeze.clicked.connect(self.freezeUser)
        self.Activate.clicked.connect(self.activateUser)
        self.TradeHistory.clicked.connect(self.openTradeHistory)
        self.OrderHistory.clicked.connect(self.openOrderHistory)

    def openOrderHistory(self):
        wallet_id = self.WalletID.text()  # Get the WalletID from input field

        if not wallet_id:
            QMessageBox.warning(self, "Input Error", "Please enter a valid WalletID.")
            return

        # Open TradeHistory window with the given WalletID
        self.trade_history_window = OrderHistoryWindow(wallet_id)
        self.trade_history_window.exec()

    def openTradeHistory(self):
        wallet_id = self.WalletID.text()  # Get the WalletID from input field

        if not wallet_id:
            QMessageBox.warning(self, "Input Error", "Please enter a valid WalletID.")
            return

        # Open TradeHistory window with the given WalletID
        self.trade_history_window = TradeHistoryWindow(wallet_id)
        self.trade_history_window.exec()

    def freezeUser(self):
        wallet_id = self.WalletID.text()  # Get the WalletID from input field
        
        if not wallet_id:
            QMessageBox.warning(self, "Input Error", "Please enter a valid WalletID.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check if user exists and is Active
        cursor.execute("SELECT Type FROM Users WHERE WalletID = ?", (wallet_id,))
        user = cursor.fetchone()

        if not user:
            QMessageBox.warning(self, "User Not Found", "No user found with the given WalletID.")
            cursor.close()
            connection.close()
            return

        current_type = user[0]

        if current_type == 'Frozen':
            QMessageBox.warning(self, "User Frozen", "This user is already frozen.")
        else:
            # Freeze the user by updating the Type column to 'Frozen'
            cursor.execute("UPDATE Users SET Type = 'Frozen' WHERE WalletID = ?", (wallet_id,))
            connection.commit()
            QMessageBox.information(self, "User Frozen", "User has been successfully frozen.")

        cursor.close()
        connection.close()

    def activateUser(self):
        wallet_id = self.WalletID.text()  # Get the WalletID from input field
        
        if not wallet_id:
            QMessageBox.warning(self, "Input Error", "Please enter a valid WalletID.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check if user exists and is Frozen
        cursor.execute("SELECT Type FROM Users WHERE WalletID = ?", (wallet_id,))
        user = cursor.fetchone()

        if not user:
            QMessageBox.warning(self, "User Not Found", "No user found with the given WalletID.")
            cursor.close()
            connection.close()
            return

        current_type = user[0]

        if current_type == 'Active':
            QMessageBox.warning(self, "User Active", "This user is already active.")
        else:
            # Activate the user by updating the Type column to 'Active'
            cursor.execute("UPDATE Users SET Type = 'Active' WHERE WalletID = ?", (wallet_id,))
            connection.commit()
            QMessageBox.information(self, "User Activated", "User has been successfully activated.")

        cursor.close()
        connection.close()

    def openTradeCheck(self):
        # Select trade ID from dropdown
        trade_id = self.TradeRequest.currentText()
        if not trade_id:
            QMessageBox.warning(self, "Trade Selection", "No trade selected. Please select a trade to proceed.")
            return

        # Open TradeCheck dialog with the selected trade ID
        self.trade_check = TradeCheck(int(trade_id))
        self.trade_check.exec()

    def rejectTrade(self):
        trade_id = self.TradeRequest.currentText()
        if not trade_id:
            QMessageBox.warning(self, "Trade Selection", "No trade selected. Please select a trade to reject.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Update status to 'Rejected'
        cursor.execute("UPDATE Trades SET Status = 'Rejected' WHERE TradeID = ?", (trade_id,))
        
        # Decrement the number of requests for the employee
        cursor.execute("UPDATE Employee SET NumberOfRequests = NumberOfRequests - 1 WHERE EmployeeID = ?", (self.employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Trade Rejected", "The trade has been rejected successfully.")
        self.populateTradeRequests()

    def acceptTrade(self):
        trade_id = self.TradeRequest.currentText()
        if not trade_id:
            QMessageBox.warning(self, "Trade Selection", "No trade selected. Please select a trade to approve.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get trade details
        cursor.execute("""
            SELECT WalletID1, WalletID2, CoinID1, CoinID2, Quantity1, Quantity2
            FROM Trades
            WHERE TradeID = ?
        """, (trade_id,))
        trade = cursor.fetchone()

        if not trade:
            QMessageBox.warning(self, "Trade Not Found", "The selected trade does not exist.")
            cursor.close()
            connection.close()
            return

        wallet_id1, wallet_id2, coin_id1, coin_id2, quantity1, quantity2 = trade

        # Check if WalletID1 has enough coins of CoinID1
        cursor.execute("SELECT Quantity FROM Wallet WHERE WalletID = ? AND CoinID = ?", (wallet_id1, coin_id1))
        wallet1_coin_quantity = cursor.fetchone()

        # If no coins are found in WalletID1 for CoinID1, set to 0
        if wallet1_coin_quantity:
            wallet1_coin_quantity = wallet1_coin_quantity[0]
        else:
            wallet1_coin_quantity = 0

        # If WalletID1 doesn't have enough coins, show an error
        if wallet1_coin_quantity < quantity1:
            QMessageBox.warning(self, "Insufficient Coins", f"Wallet {wallet_id1} does not have enough {coin_id1} coins.")
            cursor.close()
            connection.close()
            return

        # Check if WalletID2 has enough coins of CoinID2
        cursor.execute("SELECT Quantity FROM Wallet WHERE WalletID = ? AND CoinID = ?", (wallet_id2, coin_id2))
        wallet2_coin_quantity = cursor.fetchone()

        # If no coins are found in WalletID2 for CoinID2, set to 0
        if wallet2_coin_quantity:
            wallet2_coin_quantity = wallet2_coin_quantity[0]
        else:
            wallet2_coin_quantity = 0

        # If WalletID2 doesn't have enough coins, show an error
        if wallet2_coin_quantity < quantity2:
            QMessageBox.warning(self, "Insufficient Coins", f"Wallet {wallet_id2} does not have enough {coin_id2} coins.")
            cursor.close()
            connection.close()
            return

        # If both wallets have enough coins, proceed with the trade
        # Update Wallet balances

        # Wallet 1: Deduct CoinID1 and Add CoinID2
        new_wallet1_coin_quantity1 = wallet1_coin_quantity - quantity1
        cursor.execute("UPDATE Wallet SET Quantity = ? WHERE WalletID = ? AND CoinID = ?", 
                    (new_wallet1_coin_quantity1, wallet_id1, coin_id1))

        cursor.execute("SELECT Quantity FROM Wallet WHERE WalletID = ? AND CoinID = ?", 
                    (wallet_id1, coin_id2))
        wallet1_coin_quantity2 = cursor.fetchone()

        # If CoinID2 doesn't exist in Wallet1, initialize it to 0
        if wallet1_coin_quantity2:
            wallet1_coin_quantity2 = wallet1_coin_quantity2[0]
        else:
            wallet1_coin_quantity2 = 0

        # Update CoinID2 in Wallet1
        new_wallet1_coin_quantity2 = wallet1_coin_quantity2 + quantity2
        cursor.execute("UPDATE Wallet SET Quantity = ? WHERE WalletID = ? AND CoinID = ?", 
                    (new_wallet1_coin_quantity2, wallet_id1, coin_id2))

        # Wallet 2: Deduct CoinID2 and Add CoinID1
        new_wallet2_coin_quantity2 = wallet2_coin_quantity - quantity2
        cursor.execute("UPDATE Wallet SET Quantity = ? WHERE WalletID = ? AND CoinID = ?", 
                    (new_wallet2_coin_quantity2, wallet_id2, coin_id2))

        cursor.execute("SELECT Quantity FROM Wallet WHERE WalletID = ? AND CoinID = ?", 
                    (wallet_id2, coin_id1))
        wallet2_coin_quantity1 = cursor.fetchone()

        # If CoinID1 doesn't exist in Wallet2, initialize it to 0
        if wallet2_coin_quantity1:
            wallet2_coin_quantity1 = wallet2_coin_quantity1[0]
        else:
            wallet2_coin_quantity1 = 0

        # Update CoinID1 in Wallet2
        new_wallet2_coin_quantity1 = wallet2_coin_quantity1 + quantity1
        cursor.execute("UPDATE Wallet SET Quantity = ? WHERE WalletID = ? AND CoinID = ?", 
                    (new_wallet2_coin_quantity1, wallet_id2, coin_id1))

        # Update trade status to 'Approved'
        cursor.execute("UPDATE Trades SET Status = 'Approved' WHERE TradeID = ?", (trade_id,))

        # Decrement the number of requests for the employee
        cursor.execute("UPDATE Employee SET NumberOfRequests = NumberOfRequests - 1 WHERE EmployeeID = ?", 
                    (self.employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Trade Approved", "The trade has been approved successfully.")
        self.populateTradeRequests()

    def populateTradeRequests(self):
        # Populate the TradeRequest dropdown with OrderIDs where the status is 'Accepted' and EmployeeID matches.
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get pending orders
        cursor.execute("SELECT TradeID FROM Trades WHERE EmployeeID = ? AND Status = 'Accepted'", (self.employee_id,))
        trades = cursor.fetchall()

        self.TradeRequest.clear()

        # Populate dropdown with TradeID
        for trade in trades:
            trade_id = trade[0]
            self.TradeRequest.addItem(str(trade_id))

        cursor.close()
        connection.close()

    def populateRequests(self):
        #Populate the OrderRequest dropdown with OrderIDs where the status is 'Pending' and EmployeeID matches.
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get pending orders
        cursor.execute("SELECT OrderID FROM Orders WHERE EmployeeID = ? AND Status = 'Pending'", (self.employee_id,))
        orders = cursor.fetchall()

        self.OrderRequest.clear()

        # Populate dropdown with OrderID
        for order in orders:
            order_id = order[0]
            self.OrderRequest.addItem(str(order_id))

        cursor.close()
        connection.close()

    def openOrderCheck(self):
        # Select orderID from dropdown
        order_id = self.OrderRequest.currentText()
        if not order_id:
            QMessageBox.warning(self, "Order Selection", "No order selected. Please select an order to proceed.")
            return

        # Open OrderCheck dialog with the selected order ID
        self.order_check = OrderCheck(int(order_id))
        self.order_check.exec()

    def acceptOrder(self):
        order_id = self.OrderRequest.currentText()
        if not order_id:
            QMessageBox.warning(self, "Order Selection", "No order selected. Please select an order to approve.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get order details
        cursor.execute("""
            SELECT WalletID, CoinID, Quantity, Total, Type
            FROM Orders WHERE OrderID = ?
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            QMessageBox.warning(self, "Order Not Found", "The selected order does not exist.")
            cursor.close()
            connection.close()
            return

        wallet_id, coin_id, quantity, total, order_type = order

        # Get company budget and coin inventory
        cursor.execute("SELECT Budget FROM Company WHERE CompanyID = 1")
        company_budget = cursor.fetchone()[0]

        cursor.execute("SELECT Quantity FROM Inventory WHERE CoinID = ?", (coin_id,))
        inventory_quantity = cursor.fetchone()[0]

        # Get user's balance and coins
        cursor.execute("SELECT Balance FROM Users WHERE WalletID = ?", (wallet_id,))
        user_balance = cursor.fetchone()[0]

        cursor.execute("SELECT Quantity FROM Wallet WHERE WalletID = ? AND CoinID = ?", (wallet_id, coin_id))
        user_coin_quantity = cursor.fetchone()
        user_coin_quantity = user_coin_quantity[0] if user_coin_quantity else 0

        # Process based on order type
        if order_type == 'Buy':
            if inventory_quantity < quantity:
                QMessageBox.warning(self, "Insufficient Inventory", "Not enough inventory for this buy order.")
                cursor.close()
                connection.close()
                return

            if user_balance < total:
                QMessageBox.warning(self, "Insufficient Balance", "The user does not have enough balance.")
                cursor.close()
                connection.close()
                return

            # Update inventory, budget, balance, and wallet
            new_inventory_quantity = inventory_quantity - quantity
            new_company_budget = company_budget + total
            new_user_balance = user_balance - total
            new_user_coin_quantity = user_coin_quantity + quantity

        elif order_type == 'Sell':
            if company_budget < total:
                QMessageBox.warning(self, "Insufficient Company Budget", "Company budget is insufficient for this sell order.")
                cursor.close()
                connection.close()
                return

            if user_coin_quantity < quantity:
                QMessageBox.warning(self, "Insufficient User Coins", "The user does not have enough coins to sell.")
                cursor.close()
                connection.close()
                return

            # Update inventory, budget, balance, and wallet
            new_inventory_quantity = inventory_quantity + quantity
            new_company_budget = company_budget - total
            new_user_balance = user_balance + total
            new_user_coin_quantity = user_coin_quantity - quantity

        # Update the database
        cursor.execute("UPDATE Inventory SET Quantity = ? WHERE CoinID = ?", (new_inventory_quantity, coin_id))
        cursor.execute("UPDATE Company SET Budget = ? WHERE CompanyID = 1", (new_company_budget,))
        cursor.execute("UPDATE Users SET Balance = ? WHERE WalletID = ?", (new_user_balance, wallet_id))

        if user_coin_quantity == 0 and order_type == 'Buy':
            cursor.execute("INSERT INTO Wallet (WalletID, CoinID, Quantity) VALUES (?, ?, ?)", (wallet_id, coin_id, new_user_coin_quantity))
        else:
            cursor.execute("UPDATE Wallet SET Quantity = ? WHERE WalletID = ? AND CoinID = ?", (new_user_coin_quantity, wallet_id, coin_id))

        cursor.execute("UPDATE Orders SET Status = 'Approved' WHERE OrderID = ?", (order_id,))
        cursor.execute("UPDATE Employee SET NumberOfRequests = NumberOfRequests - 1 WHERE EmployeeID = ?", (self.employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Order Approved", "The order has been approved successfully.")
        self.populateRequests()

    def rejectOrder(self):
        # Reject the selected order by updating its status to 'Rejected' and decrementing employee's NumberOfRequests.
        order_id = self.OrderRequest.currentText()
        if not order_id:
            QMessageBox.warning(self, "Order Selection", "No order selected. Please select an order to reject.")
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Update status to 'Rejected'
        cursor.execute("UPDATE Orders SET Status = 'Rejected' WHERE OrderID = ?", (order_id,))
        cursor.execute("UPDATE Employee SET NumberOfRequests = NumberOfRequests - 1 WHERE EmployeeID = ?", (self.employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Order Rejected", "The order has been rejected successfully.")
        self.populateRequests()

    def goBack(self):
        self.close()

class OrderHistoryWindow(QtWidgets.QDialog):
    def __init__(self, wallet_id):
        super(OrderHistoryWindow, self).__init__()
        uic.loadUi('OrderHistory.ui', self)

        self.wallet_id = wallet_id  # Store the WalletID

        # Connect the "Done" button to close the window
        self.Done.clicked.connect(self.closeWindow)

        # Populate the order history based on WalletID
        self.populateOrderHistory()

    def populateOrderHistory(self):
        connection = pyodbc.connect(connection_string) 
        cursor = connection.cursor()

        # Get orders involving the given WalletID
        cursor.execute("""
            SELECT OrderID, WalletID, CoinID, Quantity, Total, Date, Type, Status
            FROM Orders
            WHERE WalletID = ?
            ORDER BY Date DESC
        """, (self.wallet_id,))

        orders = cursor.fetchall()
        self.OrderHistory.clear()

        # Populate QListWidget with order data
        for order in orders:
            order_id, wallet_id, coin_id, quantity, total, date, order_type, status = order
            item_text = (f"OrderID: {order_id}, Coin: {coin_id}, Quantity: {quantity}, "
                         f"Total: {total}, Date: {date}, Type: {order_type}, Status: {status}")
            item = QtWidgets.QListWidgetItem(item_text)
            self.OrderHistory.addItem(item)

        cursor.close()
        connection.close()

    def closeWindow(self):
        self.accept() 

class TradeHistoryWindow(QtWidgets.QDialog):
    def __init__(self, wallet_id):
        super(TradeHistoryWindow, self).__init__()
        uic.loadUi('TradeHistory.ui', self)

        self.wallet_id = wallet_id  # Store the WalletID

        self.Done.clicked.connect(self.closeWindow)
        # Populate the trade history based on WalletID
        self.populateTradeHistory()

    def populateTradeHistory(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Get trades involving the given WalletID 
        cursor.execute("""
            SELECT TradeID, WalletID1, WalletID2, CoinID1, CoinID2, Quantity1, Quantity2, Date, Status
            FROM Trades
            WHERE WalletID1 = ? OR WalletID2 = ?
            ORDER BY Date DESC
        """, (self.wallet_id, self.wallet_id))

        trades = cursor.fetchall()

        self.TradeHistory.clear()

        # Populate QListWidget with trade data
        for trade in trades:
            trade_id, wallet_id1, wallet_id2, coin_id1, coin_id2, quantity1, quantity2, date, status = trade
            item_text = f"TradeID: {trade_id}, Wallet1: {wallet_id1}, Wallet2: {wallet_id2}, Coins1: {coin_id1}, Coins2: {coin_id2}, Quantities1: {quantity1}, Quantities2: {quantity2}, Date: {date}, Status: {status}"
            item = QtWidgets.QListWidgetItem(item_text)
            self.TradeHistory.addItem(item)

        cursor.close()
        connection.close()
    
    def closeWindow(self):
        self.accept()

class ChangeBalance(QtWidgets.QDialog):
    def __init__(self, wallet_id, action_type="Deposit"):
        super(ChangeBalance, self).__init__()
        uic.loadUi('DepositWithdraw.ui', self)

        self.wallet_id = wallet_id
        self.action_type = action_type

        # Action Type allows us to use 1 window for Deposit and Withdraw
        self.setWindowTitle(f"{action_type} Funds")
        self.Amount.setPlaceholderText(f"Enter amount to {action_type.lower()}")

        # Connection buttons
        self.Confirm.clicked.connect(self.adjustBalance)
        self.Cancel.clicked.connect(self.close)

    def adjustBalance(self):
        amount_text = self.Amount.text()

        # Check amount
        if not amount_text.isdigit() or int(amount_text) <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid positive amount.")
            return

        amount = int(amount_text)

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check Status
        cursor.execute("SELECT Balance, Type FROM Users WHERE WalletID = ?", (self.wallet_id,))
        result = cursor.fetchone()
        
        if result and result[1] != "Active":  # If account is not active
            QMessageBox.warning(self, "Inactive Account", "Your account is not active. Please contact support.")
            cursor.close()
            connection.close()
            return

        balance = result[0]

        # Perform deposit or withdrawal based on action type
        if self.action_type == "Deposit":
            cursor.execute("UPDATE Users SET Balance = Balance + ? WHERE WalletID = ?", (amount, self.wallet_id))
        elif self.action_type == "Withdraw":
            if amount > balance:
                QMessageBox.warning(self, "Insufficient Funds", "You do not have enough balance.")
                cursor.close()
                connection.close()
                return
            cursor.execute("UPDATE Users SET Balance = Balance - ? WHERE WalletID = ?", (amount, self.wallet_id))

        connection.commit()
        cursor.close()
        connection.close()
        self.accept()

class BuyOrder(QtWidgets.QDialog):
    def __init__(self, wallet_id):
        super(BuyOrder, self).__init__()
        uic.loadUi('BuyOrder.ui', self)

        self.wallet_id = wallet_id
        self.populateCoins()

        # Connect Buttons
        self.Confirm.clicked.connect(self.processOrder)
        self.Cancel.clicked.connect(self.close)

    def populateCoins(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Get coins 
        cursor.execute("SELECT CoinID, CoinName, Price FROM Coin")
        coins = cursor.fetchall()
        
        self.CoinTable.setRowCount(len(coins))
        self.CoinTable.setColumnCount(3)
        self.CoinTable.setHorizontalHeaderLabels(["ID", "Coin Name", "Coin Value ($)"])

        for row_index, (coin_id, coin_name, price) in enumerate(coins):
            self.CoinTable.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.CoinTable.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))
            self.CoinTable.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"${price:.2f}"))

        cursor.close()
        connection.close()

    def processOrder(self):
        selected_row = self.CoinTable.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Coin Selected", "Please select a coin to buy.")
            return

        coin_id = int(self.CoinTable.item(selected_row, 0).text())
        price_text = self.CoinTable.item(selected_row, 2).text().replace("$", "")
        price = float(price_text)

        quantity_text = self.Quantity.text()
        try:
            quantity = float(quantity_text)
            if quantity <= 0 or round(quantity, 2) != quantity:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity with up to two decimal places.")
            return

        total_cost = price * quantity  # Calculate the total cost

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check if the account is active
        cursor.execute("SELECT Balance, Type FROM Users WHERE WalletID = ?", (self.wallet_id,))
        result = cursor.fetchone()
        
        if result and result[1] != "Active":  # If account is not active
            QMessageBox.warning(self, "Inactive Account", "Your account is not active. Please contact support.")
            cursor.close()
            connection.close()
            return

        # Find the employee with the lowest number of requests
        cursor.execute("SELECT TOP 1 EmployeeID FROM Employee ORDER BY NumberOfRequests ASC")
        employee = cursor.fetchone()
        employee_id = employee[0]

        # Insert order record in Orders table with calculated Total
        cursor.execute("""
            INSERT INTO Orders (WalletID, CoinID, Quantity, Total, Type, EmployeeID, Status)
            VALUES (?, ?, ?, ?, 'Buy', ?, 'Pending')
        """, (self.wallet_id, coin_id, quantity, total_cost, employee_id))

        # Update NumberOfRequests
        cursor.execute("""
            UPDATE Employee SET NumberOfRequests = NumberOfRequests + 1 WHERE EmployeeID = ?
        """, (employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Order Placed", "Your buy order has been placed successfully.")
        self.accept()

class SellOrder(QtWidgets.QDialog):
    def __init__(self, wallet_id):
        super(SellOrder, self).__init__()
        uic.loadUi('SellOrder.ui', self)

        self.wallet_id = wallet_id
        self.populateCoins()

        # Connect Confirm and Cancel buttons
        self.Confirm.clicked.connect(self.processOrder)
        self.Cancel.clicked.connect(self.close)

    def populateCoins(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Get Coins
        cursor.execute("SELECT CoinID, CoinName, Price FROM Coin")
        coins = cursor.fetchall()
        
        self.CoinTable.setRowCount(len(coins))
        self.CoinTable.setColumnCount(3)
        self.CoinTable.setHorizontalHeaderLabels(["ID", "Coin Name", "Coin Value ($)"])

        for row_index, (coin_id, coin_name, price) in enumerate(coins):
            self.CoinTable.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.CoinTable.setItem(row_index, 1, QtWidgets.QTableWidgetItem(coin_name))
            self.CoinTable.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"${price:.2f}"))

        cursor.close()
        connection.close()

    def processOrder(self):
        selected_row = self.CoinTable.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Coin Selected", "Please select a coin to buy.")
            return

        coin_id = int(self.CoinTable.item(selected_row, 0).text())
        price_text = self.CoinTable.item(selected_row, 2).text().replace("$", "")
        price = float(price_text)

        quantity_text = self.Quantity.text()
        try:
            quantity = float(quantity_text)
            if quantity <= 0 or round(quantity, 2) != quantity:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity with up to two decimal places.")
            return

        total_cost = price * quantity  # Calculate the total cost

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check if the account is active
        cursor.execute("SELECT Balance, Type FROM Users WHERE WalletID = ?", (self.wallet_id,))
        result = cursor.fetchone()
        
        if result and result[1] != "Active":  # If account is not active
            QMessageBox.warning(self, "Inactive Account", "Your account is not active. Please contact support.")
            cursor.close()
            connection.close()
            return

        # Find the employee with the lowest number of requests
        cursor.execute("SELECT TOP 1 EmployeeID FROM Employee ORDER BY NumberOfRequests ASC")
        employee = cursor.fetchone()
        employee_id = employee[0]

        # Insert order record in Orders table with calculated Total
        cursor.execute("""
            INSERT INTO Orders (WalletID, CoinID, Quantity, Total, Type, EmployeeID, Status)
            VALUES (?, ?, ?, ?, 'Sell', ?, 'Pending')
        """, (self.wallet_id, coin_id, quantity, total_cost, employee_id))

        # Update NumberOfRequests
        cursor.execute("""
            UPDATE Employee SET NumberOfRequests = NumberOfRequests + 1 WHERE EmployeeID = ?
        """, (employee_id,))

        connection.commit()
        cursor.close()
        connection.close()

        QMessageBox.information(self, "Order Placed", "Your sell order has been placed successfully.")
        self.accept() 

class OrderCheck(QtWidgets.QDialog):
    def __init__(self, order_id):
        super(OrderCheck, self).__init__()
        uic.loadUi('OrderCheck.ui', self)

        self.order_id = order_id
        self.wallet_id = None

        self.populateOrder()
        self.populateInventory()
        self.populateWalletDetails()

        # Connection Button
        self.Done.clicked.connect(self.close)

    def populateOrder(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT Orders.OrderID, Users.WalletID, Users.Balance, Coin.CoinID, Coin.CoinName, Orders.Quantity, Orders.Total, Orders.Date, Orders.Type
            FROM Orders
            JOIN Users ON Orders.WalletID = Users.WalletID
            JOIN Coin ON Orders.CoinID = Coin.CoinID
            WHERE Orders.OrderID = ?
        """, (self.order_id,))
        
        order = cursor.fetchone()
        
        # Get budget
        cursor.execute("SELECT Budget FROM Company WHERE CompanyID = 1")
        company_result = cursor.fetchone()
        company_budget = company_result[0] if company_result else 0

        if order:
            self.wallet_id = order.WalletID
            order_details = (
                f"Order ID: {order.OrderID}\n"
                f"Wallet ID: {order.WalletID}\n"
                f"Balance: ${order.Balance:.2f}\n"
                f"Coin ID: {order.CoinID}\n"
                f"Coin: {order.CoinName}\n"
                f"Quantity: {order.Quantity:.2f}\n"
                f"Total: ${order.Total:.2f}\n"
                f"Date: {order.Date.strftime('%Y-%m-%d')}\n"
                f"Type: {order.Type}\n"
                f"Company Budget: ${company_budget:.2f}"
            )
            self.DisplarOrder.setText(order_details)
        else:
            self.DisplarOrder.setText("Order details not found.")
        
        cursor.close()
        connection.close()

    def populateInventory(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        # Get inventory details
        cursor.execute("SELECT CoinID, Quantity FROM Inventory")
        inventory = cursor.fetchall()
        
        self.Inventory.setRowCount(len(inventory))
        self.Inventory.setColumnCount(2)
        self.Inventory.setHorizontalHeaderLabels(["ID", "Quantity"])
        
        for row_index, (coin_id, quantity) in enumerate(inventory):
            self.Inventory.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.Inventory.setItem(row_index, 1, QtWidgets.QTableWidgetItem(f"{quantity:.2f}"))
        
        cursor.close()
        connection.close()

    def populateWalletDetails(self):
        # Check wallet_id
        if self.wallet_id is None:
            QMessageBox.warning(self, "Error", "Wallet ID not found for this order.")
            return

        # Get wallet details
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT Coin.CoinID, Coin.CoinName, Wallet.Quantity
            FROM Wallet
            JOIN Coin ON Wallet.CoinID = Coin.CoinID
            WHERE Wallet.WalletID = ?
        """, (self.wallet_id,))
        wallet_coins = cursor.fetchall()

        self.Wallet.setRowCount(len(wallet_coins))
        self.Wallet.setColumnCount(2)
        self.Wallet.setHorizontalHeaderLabels(["Coin ID", "Quantity"])

        for row_index, (coin_id, coin_name, quantity) in enumerate(wallet_coins):
            self.Wallet.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.Wallet.setItem(row_index, 1, QtWidgets.QTableWidgetItem(f"{float(quantity):.2f}"))

        cursor.close()
        connection.close()

class TradeCheck(QtWidgets.QDialog):
    def __init__(self, trade_id):
        super(TradeCheck, self).__init__()
        uic.loadUi('TradeCheck.ui', self)

        self.trade_id = trade_id
        self.wallet_id1 = None
        self.wallet_id2 = None

        self.populateTrade()
        self.populateWalletDetails()

        # Connection Button
        self.Done.clicked.connect(self.close)

    def populateTrade(self):
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Get trade details
        cursor.execute("""
            SELECT Trades.TradeID, Trades.WalletID1, Trades.WalletID2, Trades.CoinID1, Trades.CoinID2, 
                   Trades.Quantity1, Trades.Quantity2, Trades.Date, Trades.Status
            FROM Trades
            WHERE Trades.TradeID = ?
        """, (self.trade_id,))
        
        trade = cursor.fetchone()

        if trade:
            self.wallet_id1 = trade.WalletID1
            self.wallet_id2 = trade.WalletID2
            trade_details = (
                f"Trade ID: {trade.TradeID}\n"
                f"Buyer WalletID: {trade.WalletID1}\n"
                f"Buyer CoinID: {trade.CoinID1}\n"
                f"Buyer Quantity: {trade.Quantity1:.2f}\n"
                f"Seller WalletID: {trade.WalletID2}\n"
                f"Seller CoinID: {trade.CoinID2}\n"
                f"Seller Quantity: {trade.Quantity2:.2f}\n"
                f"Date: {trade.Date.strftime('%Y-%m-%d')}\n"
                f"Status: {trade.Status}\n"
            )
            self.DisplayTrade.setText(trade_details)
        else:
            self.DisplayTrade.setText("Trade details not found.")
        
        cursor.close()
        connection.close()

    def populateWalletDetails(self):
        # Check wallet IDs
        if self.wallet_id1 is None or self.wallet_id2 is None:
            QMessageBox.warning(self, "Error", "Wallet IDs not found for this trade.")
            return

        # Get wallet details for both wallets
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT Coin.CoinID, Coin.CoinName, Wallet.Quantity
            FROM Wallet
            JOIN Coin ON Wallet.CoinID = Coin.CoinID
            WHERE Wallet.WalletID = ?
        """, (self.wallet_id1,))
        wallet1_coins = cursor.fetchall()

        self.Wallet1.setRowCount(len(wallet1_coins))
        self.Wallet1.setColumnCount(2)
        self.Wallet1.setHorizontalHeaderLabels(["Coin ID", "Quantity"])

        for row_index, (coin_id, coin_name, quantity) in enumerate(wallet1_coins):
            self.Wallet1.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.Wallet1.setItem(row_index, 1, QtWidgets.QTableWidgetItem(f"{float(quantity):.2f}"))

        cursor.execute("""
            SELECT Coin.CoinID, Coin.CoinName, Wallet.Quantity
            FROM Wallet
            JOIN Coin ON Wallet.CoinID = Coin.CoinID
            WHERE Wallet.WalletID = ?
        """, (self.wallet_id2,))
        wallet2_coins = cursor.fetchall()

        self.Wallet2.setRowCount(len(wallet2_coins))
        self.Wallet2.setColumnCount(2)
        self.Wallet2.setHorizontalHeaderLabels(["Coin ID", "Quantity"])

        for row_index, (coin_id, coin_name, quantity) in enumerate(wallet2_coins):
            self.Wallet2.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(coin_id)))
            self.Wallet2.setItem(row_index, 1, QtWidgets.QTableWidgetItem(f"{float(quantity):.2f}"))

        cursor.close()
        connection.close()

class SuperAdminLogin(QtWidgets.QMainWindow):
    backLogin = pyqtSignal()

    def __init__(self):
        super(SuperAdminLogin, self).__init__()
        try:
            uic.loadUi('SuperAdminLogin.ui', self)
            print("SuperAdminLogin UI loaded successfully.")
        except Exception as e:
            print(f"Error loading SuperAdminLogin UI: {e}")

        self.Login.clicked.connect(self.handleSuperAdminLogin)
        self.Back.clicked.connect(self.goBack)

    def handleSuperAdminLogin(self):
        print("SuperAdmin Login Attempt")
        employee_id = self.WalletID.text()
        password = self.Password.text()

        # Check Input
        if not employee_id or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both EmployeeID and Password.")
            return

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Check Credentials
            cursor.execute("SELECT EmployeeID FROM Employee WHERE EmployeeID = ? AND Password = ? AND isSuperAdmin = 1", (employee_id, password))
            result = cursor.fetchone()

            if result:
                QMessageBox.information(self, "Login Successful", f"Welcome, Super Admin ID: {employee_id}")
                self.WalletID.clear()
                self.Password.clear()
                # Open SuperAdmin Window
                self.super_admin_window = SuperAdminWindow(self, employee_id)
                self.super_admin_window.show()
                self.close()
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid EmployeeID or Password.")
        except Exception as e:
            print(f"Error during SuperAdmin login: {e}")
        finally:
            cursor.close()
            connection.close()

    def goBack(self):
        print("Going back to login.")
        self.backLogin.emit()
        self.close()

class SuperAdminWindow(QtWidgets.QMainWindow):
    def __init__(self, super_admin_login_window, employee_id):
        super(SuperAdminWindow, self).__init__()
        uic.loadUi('SuperAdmin.ui', self)

        # Store references
        self.super_admin_login_window = super_admin_login_window
        self.employee_id = employee_id

        # Connection buttons
        self.Back.clicked.connect(self.goBack)
        self.insert.clicked.connect(self.insertCoin)
        self.update.clicked.connect(self.updateCoin)
        self.delete_2.clicked.connect(self.deleteCoin)

    def insertCoin(self):
        # Get user inputs from line edits
        coin_name = self.insertCoinName.text()
        price = self.insertCoinPrice.text()

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Insert new coin
        insert_query = """
        INSERT INTO Coin (CoinName, Price)
        VALUES (?, ?)
        """

        cursor.execute(insert_query, (coin_name, price))
        connection.commit()

        # Confirmation message
        QMessageBox.information(self, "Coin Inserted", f"Coin Name: {coin_name} has been inserted successfully.")

        cursor.close()
        connection.close()

        # Clear line edits
        self.CoinName.clear()
        self.Price.clear()


    def updateCoin(self):
        # Get user inputs from line edits
        coin_name = self.updateCoinName.text()
        price = self.updateCoinPrice.text()

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Update coin
        update_query = """
        UPDATE Coin
        SET Price = ?
        WHERE CoinName = ?
        """

        cursor.execute(update_query, (price, coin_name))
        connection.commit()

        # Confirmation message
        QMessageBox.information(self, "Coin Updated", f"Coin Name: {coin_name} has been updated successfully.")

        cursor.close()
        connection.close()

        # Clear line edits
        self.updateCoinName.clear()
        self.updateCoinPrice.clear()

    def deleteCoin(self):
        # Get user inputs from line edits
        coin_name = self.deleteCoinName.text()

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Delete coin
        delete_query = """
        DELETE FROM Coin
        WHERE CoinName = ?
        """

        cursor.execute(delete_query, (coin_name,))
        connection.commit()

        # Confirmation message
        QMessageBox.information(self, "Coin Deleted", f"Coin Name: {coin_name} has been deleted successfully.")

        cursor.close()
        connection.close()

        # Clear line edits
        self.deleteCoinName.clear()

    def goBack(self):
        self.super_admin_login_window.show()
        self.close()


def main():
    app = QApplication(sys.argv)
    window = UI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
