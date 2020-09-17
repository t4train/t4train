//
//  BluetoothViewController.swift
//  Mobile Datahandler
//
//

import UIKit

class BluetoothViewController: UITableViewController, DataHandler {
    var SENSOR_ID: String = "BLE"
    
    func latestDataSample() -> String? {
        return nil
    }
    
    func title() -> String {
        return "BluetoothViewController"
    }
    
    func enable(successHandler: (Bool) -> ()) {
        successHandler(false)
    }
    
    func disable() {
        
    }
    
    func updateString() {
        
    }
    
    func viewController() -> UIViewController {
        return self
    }
    

    override func viewDidLoad() {
        super.viewDidLoad()

        // Do any additional setup after loading the view.
    }


    /*
    // MARK: - Navigation

    // In a storyboard-based application, you will often want to do a little preparation before navigation
    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        // Get the new view controller using segue.destination.
        // Pass the selected object to the new view controller.
    }
    */

}
