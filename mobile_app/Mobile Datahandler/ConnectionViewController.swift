//
//  ConnectionViewController.swift
//  Mobile Datahandler
//
//

import UIKit
import Network

class ConnectionViewController: UIViewController, UITextFieldDelegate {
    
    @IBOutlet weak var connectionSegment: UISegmentedControl!
    @IBOutlet weak var activityIndicator: UIActivityIndicatorView!
    @IBOutlet weak var statusLabel: UILabel!
    @IBOutlet weak var udpStack: UIStackView!
    @IBOutlet weak var ipTextField: UITextField!
    @IBOutlet weak var retryButton: UIButton!
    
    let IP_DEFAULTS_KEY = "t4t-ip"
    
    override func viewDidLoad() {
        super.viewDidLoad()
        KeyboardAvoiding.avoidingView = view
        ipTextField.delegate = self
        
        // if we have a preloaded IP, restore it
        if let ip = UserDefaults.standard.string(forKey: IP_DEFAULTS_KEY), ip != "" {
            ipTextField.text = ip
            UDPManager.shared.hostUDP = NWEndpoint.Host(ip)
        } else {
            UserDefaults.standard.set(ipTextField.text, forKey: IP_DEFAULTS_KEY)
            UDPManager.shared.hostUDP = NWEndpoint.Host(ipTextField.text ?? "")
        }
        retryButton.isHidden = true
        
        // default connection type
        ConnectionManager.shared.setConnectionType(.UDP, successHandler: connectionCompletionHandler(success:))
        NotificationCenter.default.addObserver(self, selector: #selector(enteredForeground), name: UIApplication.willEnterForegroundNotification, object: nil)
    }
    
    @objc func enteredForeground() { // attempt to reconnect when we leave and re-enter foreground
        ConnectionManager.shared.setConnectionType(ConnectionManager.shared.connectionType, successHandler: connectionCompletionHandler(success:))
    }
    
    @IBAction func segmentChanged(_ sender: UISegmentedControl) {
        tryConnect()
    }
    
    func tryConnect() {
        showPendingConnection()
        
        if connectionSegment.selectedSegmentIndex == 0 {
            udpStack.isHidden = false
            ConnectionManager.shared.setConnectionType(.UDP, successHandler: connectionCompletionHandler(success:))
        } else {
            udpStack.isHidden = true
            ConnectionManager.shared.setConnectionType(.Bluetooth, successHandler: connectionCompletionHandler(success:))
        }
    }
    
    func connectionCompletionHandler(success: Bool) {
        if success {
            self.showSuccessfulConnection()
        } else {
            self.showFailedConnection()
        }
    }
    
    func showPendingConnection() {
        DispatchQueue.main.async {
            self.activityIndicator.startAnimating()
            self.activityIndicator.alpha = 1 // dont use hiding
            self.statusLabel.text = "Attempting connection..."
        }
    }
    
    func showSuccessfulConnection() {
        DispatchQueue.main.async {
            self.activityIndicator.stopAnimating()
            self.activityIndicator.alpha = 0 // dont hide it
            
            if ConnectionManager.shared.connectionType == .UDP {
                self.statusLabel.text = "UDP stream connected"
                self.ipTextField.textColor = .black
            } else {
                self.statusLabel.text = "Bluetooth connected"
            }
            
            self.retryButton.isHidden = true
        }
    }
    
    func showFailedConnection() {
        DispatchQueue.main.async {
            self.activityIndicator.stopAnimating()
            self.activityIndicator.alpha = 0 // dont hide it
            if ConnectionManager.shared.connectionType == .UDP {
                self.statusLabel.text = "UDP Connection Failed. Check IP."
                self.ipTextField.textColor = .red
            } else {
                // could get more details to say whether its bc we dont have bluetooth
                // permissions or because the peripheral was never found
                self.statusLabel.text = "Bluetooth LE Connection Failed."
            }
            
            self.retryButton.isHidden = false
        }
    }
    
    @IBAction func retryConnectingPressed(_ sender: Any) {
        tryConnect()
    }
    
    func textFieldDidBeginEditing(_ textField: UITextField) {
        ipTextField.textColor = .black // remove red color if we had an error
    }
    
    func textFieldDidEndEditing(_ textField: UITextField) {
        // save the ip to user defaults
        UserDefaults.standard.set(ipTextField.text, forKey: IP_DEFAULTS_KEY)
        if ipTextField.text == nil || ipTextField.text == "" {
            ipTextField.text = "0.0.0.0"
        }
        UDPManager.shared.hostUDP = NWEndpoint.Host(ipTextField.text ?? "0.0.0.0")
        ipTextField.resignFirstResponder()
    }
    
    func textFieldShouldReturn(_ textField: UITextField) -> Bool {
        ipTextField.resignFirstResponder()
        return true
    }
}
