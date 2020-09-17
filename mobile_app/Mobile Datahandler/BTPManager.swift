//
//  BTPManager.swift
//  nRF Demo
//
//

import Foundation
import CoreBluetooth

// Bluetooth Peripheral Manager
class BTPManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate, CBPeripheralManagerDelegate, MessageSender {
    
    static let shared = BTPManager()
    var peripheralManager: CBPeripheralManager!
    
    var cbManager: CBCentralManager!
    private var peripherals: [CBPeripheral?] = []
    var uuidFilterList: [CBUUID] = []
    
    private var centralDelegates: [CBCentralManagerDelegate] = []
    private var peripheralDelegates: [UUID: [CBPeripheralDelegate]] = [:]
    
    let service = CBUUID(nsuuid: UUID(uuidString: "AAAAAAA0-B5A3-F393-E0A9-E50E24DCCA9E")!)
    let txID = CBUUID(nsuuid: UUID(uuidString: "AAAAAAA1-B5A3-F393-E0A9-E50E24DCCA9E")!)
    let rxID = CBUUID(nsuuid: UUID(uuidString: "AAAAAAA2-B5A3-F393-E0A9-E50E24DCCA9E")!)
    var txChar: CBMutableCharacteristic!
    var rxChar: CBMutableCharacteristic!
    var rxSubscribed = false
    var cbCentral: CBCentral?
    var myService: CBMutableService!
    
    private override init() {
        super.init()
        cbManager = CBCentralManager(delegate: self, queue: nil)
        peripheralManager = CBPeripheralManager(delegate: self, queue: .global(qos: .userInitiated), options: nil)
    }
    
    func sendMessage(msg: String) {
        if let central = cbCentral, rxSubscribed {
//            print(msg)
            peripheralManager.updateValue(msg.data(using: .utf8)!, for: rxChar, onSubscribedCentrals: [central])
        }
    }
    
    func disconnect() {
        successHandler = nil
        peripheralManager.stopAdvertising()
    }
    
    var successHandler: ((Bool) -> Void)? = nil
    func attemptConnect(successHandler: ((Bool) -> Void)?) {
        self.successHandler = successHandler
        if myService != nil { // easy check to see if we've already tried to start advertising in the past, or else there's no point
            peripheralManager.startAdvertising([CBAdvertisementDataLocalNameKey : "T4TApp",
            CBAdvertisementDataServiceUUIDsKey : [service]])
        }
    }
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn {
            txChar = CBMutableCharacteristic(type:  txID, properties: [.notify, .write, .read], value: nil, permissions: [.writeable])
            rxChar = CBMutableCharacteristic(type: rxID, properties: [.notify, .read], value: nil, permissions: [.readable])
            myService = CBMutableService(type: service, primary: true)
            
            myService.characteristics = [txChar, rxChar]
            peripheralManager.add(myService)
            peripheralManager.startAdvertising([CBAdvertisementDataLocalNameKey : "T4TApp",
                                                CBAdvertisementDataServiceUUIDsKey : [service]])
        }
    }
    
    func peripheralManagerDidStartAdvertising(_ peripheral: CBPeripheralManager, error: Error?) {
        print("Started advertising")
        if let handler = successHandler {
            handler(true)
            successHandler = nil
        }
    }
    
    func peripheralManager(_ peripheral: CBPeripheralManager, didReceiveWrite requests: [CBATTRequest]) {
        if let stringData = requests.first?.value, let str = String(data: stringData, encoding: .utf8) {
            print("received write: \(str)")
            peripheralManager.respond(to: requests.first!, withResult: .success)
        } else {
            print("received write with no value")
            peripheralManager.respond(to: requests.first!, withResult: .insufficientResources)
        }
    }
    
    func peripheralManager(_ peripheral: CBPeripheralManager, central: CBCentral, didSubscribeTo characteristic: CBCharacteristic) {
        print("subscribed")
        cbCentral = central // remember the central to respond to
//        peripheral.updateValue("Mobile hello!".data(using: .utf8)!, for: rxChar, onSubscribedCentrals: [central])
        rxSubscribed = true
//        SensorBuffer.shared.shouldSendData = true
//        request.value = [myCharacteristic.value
//        subdataWithRange:NSMakeRange(request.offset,
//        myCharacteristic.value.length - request.offset)];
    }
    
//    func peripheralManagerIsReady(toUpdateSubscribers peripheral: CBPeripheralManager) {
//        print("ready to update subcribers")
//    }
    
    func peripheralManager(_ peripheral: CBPeripheralManager, central: CBCentral, didUnsubscribeFrom characteristic: CBCharacteristic) {
        print("unsubscribed")
//        SensorBuffer.shared.shouldSendData = false
    }
    
    func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
        switch peripheral.state {
        case .poweredOn:
            print("powered on")
        case .poweredOff:
            print("poweredOff")
        case .resetting:
            print("resetting")
        case .unauthorized:
            print("unauthorized")
        case .unknown:
            print("unknown")
        case .unsupported:
            print("unsupported")
        default:
            print("undocumented state")
        }
    }
    
    
}
