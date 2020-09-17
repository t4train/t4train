//
//  GyroscopeViewController.swift
//  Mobile Datahandler
//
//

import UIKit
import CoreMotion

class GyroscopeViewController: UIViewController, DataHandler, UITextFieldDelegate {
    let SENSOR_ID = "gyro" // unique to this sensor, used for sensorbuffer differentiation
    
    @IBOutlet weak var rateTextField: UITextField!
    @IBOutlet weak var rateSlider: UISlider!
    var sampleRate = 60.0 {
        didSet {
            motionManager.gyroUpdateInterval = 1 / sampleRate
        }
    }
    
    // Apple class that gives gyroscope data
    private lazy var motionManager = CMMotionManager()
    
    override init(nibName nibNameOrNil: String?, bundle nibBundleOrNil: Bundle?) {
        super.init(nibName: nibNameOrNil, bundle: nibBundleOrNil)
        motionManager.gyroUpdateInterval = 1 / sampleRate // sampleRate didSet not triggered in init
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
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
        return "Gyroscope"
    }
    
    var callbackCompletion: ((Bool) -> ())? = nil
    var latestSample: CMGyroData?
    func enable(successHandler: @escaping (Bool) -> ()) {
        if motionManager.isGyroAvailable {
            successHandler(true)
        }
        motionManager.startGyroUpdates(to: .main) { (data, error) in
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
            SensorBuffer.shared.pushUpdate(sample: [data.rotationRate.x,
                                                    data.rotationRate.y,
                                                    data.rotationRate.z],
                                           sensorUniqueId: self.SENSOR_ID)
        }
    }
    
    func disable() {
        motionManager.stopGyroUpdates()
        // must tell sensor buffer that we no longer need gyro
        // updates for next sample update to be sent to device
        SensorBuffer.shared.stopUpdates(forId: SENSOR_ID)
        latestSample = nil
    }
    
    func latestDataSample() -> String? {
        if let s = latestSample {
            return String(format: "x:%+.2f y:%+.2f, z:%+.2f", s.rotationRate.x, s.rotationRate.y, s.rotationRate.z)
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
