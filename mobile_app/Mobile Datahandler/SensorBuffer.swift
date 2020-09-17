//
//  SensorBuffer.swift
//  Mobile Datahandler
//
//

import Foundation
import CoreMotion
import UIKit

class SensorBuffer {
    static let shared = SensorBuffer()
    
    // stores batch of responses from active sensors to ensure that
    // samples sent are symmetric / same count
    private var bufferSemaphore = DispatchSemaphore(value: 1)
    var shouldSendData = false
    
    // use ids unique to each sensor data provider as keys
    private var messageBuffer: [String:String] = [:]
    private var channelReadyFlags: [String:Bool] = [:]
    
    // assumes buffer semaphore is held over duration of call =
    private func sendPushedSamples() {
        // if we're actively sending data, ensure that the most updated data for this sensor is marked as ready
        if !channelReadyFlags.values.contains(false) { // we have as many pending messages as needed
            ConnectionManager.shared.sendMessage(msg: messageBuffer.values.joined())
            channelReadyFlags.keys.forEach {channelReadyFlags[$0] = false}
        }
    }
    
    // MARK: - New Interface for sensor buffer
    
    /**
     Push updated data for a
     
     - Parameter stringRepresentation: This
     - Parameter viewController: That
     */
    func pushUpdate(sample: [Double], sensorUniqueId: String) {
        if self.shouldSendData {
            self.bufferSemaphore.wait()
            self.messageBuffer[sensorUniqueId] = "&\(sensorUniqueId):\(sample.map {String($0)}.joined(separator: ",")):"
            self.channelReadyFlags[sensorUniqueId] = true
            self.sendPushedSamples()
            self.bufferSemaphore.signal()
        }
    }
    
    /**
    Push updated data for a
    
    - Parameter stringRepresentation: This
    - Parameter viewController: That
    */
    func stopUpdates(forId sensorUniqueId: String) {
        // when we stop gryo updates, the dataframe being sent should decrease in size
        self.bufferSemaphore.wait()
        self.messageBuffer.removeValue(forKey: sensorUniqueId)
        self.channelReadyFlags.removeValue(forKey: sensorUniqueId)
        self.bufferSemaphore.signal()
    }
}
