//
//  DataHandlerCell.swift
//  Mobile Datahandler
//
//

import UIKit

class DataHandlerCell: UITableViewCell {
    
    @IBOutlet weak var connectSwitch: UISwitch!
    @IBOutlet weak var nameLabel: UILabel!
    @IBOutlet weak var infoLabel: UILabel!
    @IBOutlet weak var activityIndicator: UIActivityIndicatorView!
    var timer: Timer?
    
    var dataHandler: DataHandler? {
        didSet {
            if let handler = dataHandler {
                nameLabel.text = handler.title()
                connectSwitch.isHidden = false
            }
        }
    }

    override func awakeFromNib() {
        super.awakeFromNib()
        // Initialization code
        connectSwitch.addTarget(self, action: #selector(toggledSwitch(sender:)), for: .valueChanged)
        activityIndicator.isHidden = true
        connectSwitch.isHidden = true
        connectSwitch.isOn = false
        connectSwitch.isUserInteractionEnabled = true
    }

    override func setSelected(_ selected: Bool, animated: Bool) {
        super.setSelected(selected, animated: animated)

        // Configure the view for the selected state
    }
    
    @objc func toggledSwitch(sender: UISwitch) {
        if sender.isOn {
            activityIndicator.isHidden = false
            activityIndicator.startAnimating()
            
            sender.isUserInteractionEnabled = false
            sender.alpha = 0.5
            
            dataHandler?.enable(successHandler: { success in
                if !success {
                    sender.isOn = false
                } else {
                    self.timer = Timer(timeInterval: 0.1, repeats: true, block: { (t) in
                        DispatchQueue.main.async {
                            self.infoLabel.text = self.dataHandler?.latestDataSample() ?? "Inactive"
                        }
                    })
                    RunLoop.current.add(self.timer!, forMode: RunLoop.Mode.default)
                }
                sender.isUserInteractionEnabled = true
                sender.alpha = 1
                self.activityIndicator.isHidden = true
                self.activityIndicator.stopAnimating()
            })
        } else {
            dataHandler?.disable()
            infoLabel.text = "Inactive"
            self.timer?.invalidate()
            self.timer = nil
        }
    }
    

    
}
