//
//  DataHandler.swift
//  Mobile Datahandler
//
//

import Foundation
import UIKit


// defining functionality expected by modules that handle sensor data collection.
protocol DataHandler {
    /**
    Short string identifier unique to the sensor in question. Example: "acc" for accelerometer.
    */
    
    var SENSOR_ID: String { get } // unique to this sensor, used for sensorbuffer differentiation
    /**
     Return the display name of the view controller. e.g. "Accelerometer".
     */
    func title() -> String
    
    /**
     Tells the receiver to start listening for samples, and call completion(Bool) indicating success (true) or failure (false).
     - Parameter completion: called on determination of successfully enabling sensor feedback (true) or failure (false).
    */
    func enable(successHandler: @escaping (Bool) -> ())
                                                  
    /**
     Tell sthe receiver to stop listening for samples.
     */
    func disable()
    
    /**
     Requests string representing the latest sample batch. nil if disabled. e.g. ("1.0, 0.0, 0.0" for an accelerometer's x, y, z channels).
     */
    func latestDataSample() -> String?
                                                    
    /**
     Return the current instance of the view controller. This allows us to get around Swift's inability to treat protocol-conforming objects as existentials.
     */
    func viewController() -> UIViewController
}

