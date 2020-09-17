//
//  AccelerometerViewController.swift
//  Mobile Datahandler
//
//

import UIKit
import CoreMotion

class AccelerometerViewController: UIViewController, DataHandler, UITextFieldDelegate {
    var SENSOR_ID: String = "acc"
    
    @IBOutlet weak var rateTextField: UITextField!
    @IBOutlet weak var rateSlider: UISlider!
    var sampleRate = 60.0 {
        didSet {
            motionManager.accelerometerUpdateInterval = 1 / sampleRate
        }
    }
    
    override init(nibName nibNameOrNil: String?, bundle nibBundleOrNil: Bundle?) {
        super.init(nibName: nibNameOrNil, bundle: nibBundleOrNil)
        motionManager.accelerometerUpdateInterval = 1 / sampleRate // sampleRate didSet not triggered in init
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    // Apple class that gives accelerometer data
    private lazy var motionManager = CMMotionManager()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // Do any additional setup after loading the view.
        rateSlider.minimumValue = 1.0
        rateSlider.maximumValue = 100
        rateTextField.text = "\(Int(sampleRate))"
        rateSlider.value = Float(sampleRate)
        rateTextField.delegate = self
    }
    
    // MARK: - DataHandler Protocol
    
    func viewController() -> UIViewController {
        return self
    }
    
    func title() -> String {
        return "Accelerometer"
    }
    
    var callbackCompletion: ((Bool) -> ())? = nil
    var latestSample: CMAccelerometerData?
    func enable(successHandler: @escaping (Bool) -> ()) {
        successHandler(motionManager.isAccelerometerAvailable)
        motionManager.startAccelerometerUpdates(to: .main) { (data, error) in
            if let error = error {
                print("error: \(error)") // consider extra fallback behavior for failures here
                successHandler(false)
                return
            }
            
            guard let data = data else {
                print("data is nil")
                successHandler(false)
                return
            }
            
            // successfully got motion data, update queue
            self.latestSample = data
            SensorBuffer.shared.pushUpdate(sample: [data.acceleration.x,
                                                    data.acceleration.y,
                                                    data.acceleration.z],
                                           sensorUniqueId: self.SENSOR_ID)
        }
    }
    
    func disable() {
        motionManager.stopAccelerometerUpdates()
        // must tell sensor buffer that we no longer need acc
        // updates for next sample update to be sent to device
        SensorBuffer.shared.stopUpdates(forId: SENSOR_ID)
        latestSample = nil
    }
    
    func latestDataSample() -> String? {
        if let s = latestSample {
            return String(format: "x:%+.2f y:%+.2f, z:%+.2f", s.acceleration.x, s.acceleration.y, s.acceleration.z)
        } else {
            return nil
        }
    }
    
    // MARK: - Textfield Delegate
    
    func textFieldShouldEndEditing(_ textField: UITextField) -> Bool {
        textField.resignFirstResponder()
        return true
    }
    
    func textFieldShouldReturn(_ textField: UITextField) -> Bool {
        textField.resignFirstResponder()
        return true
    }
    
    func textFieldDidEndEditing(_ textField: UITextField) {
        if let str = textField.text, let floatValue = Float(str) {
            setRateSliderValue(value: floatValue)
            sampleRate = Double(floatValue)
        } else {
            // if textfield not parseable, fallaback on slider value
            sampleRate = getRateSliderValue()
            textField.text = String(format: "%.2f", sampleRate)
        }
    }

    // MARK: - Helpers
    
    // we only want int values from the slider
    func getRateSliderValue() -> Double {
        Double(Int(rateSlider.value))
    }
    
    func setRateSliderValue(value: Float) {
        rateSlider.value = value // but let slider get set by textfield to fraction
    }
        
    @IBAction func rateSliderChanged(_ sender: Any) {
        sampleRate = getRateSliderValue()
        rateTextField.text = String(format: "%.1f", sampleRate)
    }
}
