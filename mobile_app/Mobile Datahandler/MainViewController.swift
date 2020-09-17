//
//  ViewController.swift
//  Mobile Datahandler
//
//

import UIKit

class MainViewController: UIViewController, UITableViewDelegate, UITableViewDataSource{
    
    @IBOutlet weak var tableView: UITableView!
    
    let controllers: [DataHandler] = [
        AccelerometerViewController(nibName: nil, bundle: nil),
        GyroscopeViewController(nibName: nil, bundle: nil),
    ]
    let CELL_ID = "DataHandlerCell"
    
    override func viewDidLoad() {
        super.viewDidLoad()
        // Do any additional setup after loading the view.
        tableView.delegate = self
        tableView.dataSource = self
        tableView.register(UINib(nibName: "DataHandlerCell", bundle: nil), forCellReuseIdentifier: CELL_ID)
//        PeerManager.shared.start()
        let _ = BTPManager.shared // get manager to start advertising
        
        tableView.rowHeight = 70
    }
    
    // MARK: - Table
    
    func numberOfSections(in tableView: UITableView) -> Int {
        return 1
    }
    
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return controllers.count
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        if let cell = tableView.dequeueReusableCell(withIdentifier: CELL_ID) as? DataHandlerCell {
//            cell.nameLabel.text = controllers[indexPath.row].title()
            cell.dataHandler = controllers[indexPath.row]
            return cell
        }
        
        fatalError("Unrecognized cell class")
    }
    
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        navigationController?.pushViewController(controllers[indexPath.row].viewController(), animated: true)
    }
}

