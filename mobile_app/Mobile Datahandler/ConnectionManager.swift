//
//  ConnectionManager.swift
//  Mobile Datahandler
//
//

import Foundation

protocol MessageSender {
    func sendMessage(msg: String)
    func attemptConnect(successHandler: ((Bool) -> Void)?)
    func disconnect()
}

class ConnectionManager: MessageSender {
    
    enum ConnectionType {
        case UDP, Bluetooth
    }
    
    static let shared = ConnectionManager()
    var connectionType = ConnectionType.UDP
    
    init() {
        let _ = BTPManager.shared
        let _ = UDPManager.shared
    }
    
    // sets connection type AND attempts to connect
    func setConnectionType(_ type: ConnectionType, successHandler: ((Bool) -> Void)?) {
        self.connectionType = type
        attemptConnect(successHandler: successHandler)
    }
    
    // called if we already set connection type then disconnected.
    func attemptConnect(successHandler: ((Bool) -> Void)?) {
        // nothing to do
        let wrapper = { (success: Bool) in
            SensorBuffer.shared.shouldSendData = success
            successHandler?(success)
        }
        switch connectionType {
        case .UDP:
            UDPManager.shared.attemptConnect(successHandler: wrapper)
        case .Bluetooth:
            BTPManager.shared.attemptConnect(successHandler: successHandler)
        }
    }
    
    func disconnect() {
        SensorBuffer.shared.shouldSendData = false
    }
    
    func sendMessage(msg: String) {
        switch connectionType {
        case .UDP:
            UDPManager.shared.sendMessage(msg: msg)
        case .Bluetooth:
            BTPManager.shared.sendMessage(msg: msg)
        }
//        if let central = cbCentral, rxSubscribed {
//            print(msg)
//            peripheralManager.updateValue(msg.data(using: .utf8)!, for: rxChar, onSubscribedCentrals: [central])
//        }
    }
}
