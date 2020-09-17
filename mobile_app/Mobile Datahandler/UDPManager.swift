//
//  UDPManager.swift
//  Mobile Datahandler
//
//

import Foundation
import Network
import UIKit

class UDPManager: MessageSender {
    
    static let shared = UDPManager()
    
    var connection: NWConnection?
    var portUDP: NWEndpoint.Port = 6789 // same port always specified in t4train script
    
    // must be modified by the user
    var hostUDP: NWEndpoint.Host = "10.0.0.3" {
        didSet {
            connectToUDP(hostUDP, portUDP, successHandler: nil)
        }
    }
    
    // MARK: - Message Sender
    
    func attemptConnect(successHandler: ((Bool) -> Void)?) {
        connectToUDP(hostUDP, portUDP, successHandler: successHandler)
    }
    
    func disconnect() {
        self.connection?.cancel()
    }
    
    func sendMessage(msg: String) {
        sendUDP(msg)
    }
    
    // MARK: - Private
    
    private func connectToUDP(_ hostUDP: NWEndpoint.Host, _ portUDP: NWEndpoint.Port, successHandler: ((Bool) -> Void)?) {
        // Transmitted message:
        //        let messageToUDP = "HELLO:\(UIDevice.current.name)"
        self.connection = NWConnection(host: hostUDP, port: portUDP, using: .udp)
        
        self.connection?.stateUpdateHandler = { (newState) in
            print("This is stateUpdateHandler:")
            switch newState {
            case .ready:
                print("State: Ready for ip: \(hostUDP)\n")
                successHandler?(true)
                //                self.sendUDP(messageToUDP)
                return
            //                self.receiveUDP()
            case .setup:
                print("State: Setup\n")
            case .cancelled:
                print("State: Cancelled\n")
            case .preparing:
                print("State: Preparing\n")
            case .failed(let error):
                print("error: ", error)
            case .waiting(let error):
                print("error: ", error)
            default:
                print("error: unkown state")
            }
            successHandler?(false)
        }
        
        self.connection?.start(queue: .global())
    }
    
    func sendUDP(_ content: Data) {
        DispatchQueue.global(qos: .userInitiated).async {
            self.connection?.send(content: content, completion: NWConnection.SendCompletion.contentProcessed(({ (NWError) in
                if (NWError == nil) {
                    //                print("Data was sent to UDP")
                } else {
                    print("ERROR! Error when data (Type: Data) sending. NWError: \n \(NWError!)")
                }
            })))
            
        }
    }
    
    func sendUDP(_ content: String) {
        DispatchQueue.global(qos: .userInitiated).async {
            let contentToSendUDP = content.data(using: String.Encoding.utf8)
            self.connection?.send(content: contentToSendUDP, completion: NWConnection.SendCompletion.contentProcessed(({ (NWError) in
                if (NWError == nil) {
                    //                print("Data was sent to UDP")
                } else {
                    print("ERROR! Error when data (Type: Data) sending. NWError: \n \(NWError!)")
                }
            })))
        }
    }
    
    func receiveUDP() {
        self.connection?.receiveMessage { (data, context, isComplete, error) in
            if (isComplete) {
                print("Receive is complete")
                if (data != nil) {
                    let backToString = String(decoding: data!, as: UTF8.self)
                    print("Received message: \(backToString)")
                } else {
                    print("Data == nil")
                }
            }
        }
    }
    
}
