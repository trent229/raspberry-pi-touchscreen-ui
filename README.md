# Raspberry Pi Touchscreen UI

A lightweight touchscreen human-machine interface built for the Raspberry Pi
Zero W. The application uses Python and Tkinter to provide a responsive,
full-screen control center without requiring a web browser or external Python
packages.

## Features

- Full-screen touch-first layout
- Live clock and date
- Processor-temperature monitoring
- Memory and storage usage
- Wi-Fi quality and IP-address status
- System-information page
- Interactive touch-test canvas
- Confirmed restart and shutdown controls
- Automatic startup with the Raspberry Pi desktop
- Keyboard shortcuts for development and troubleshooting

## Hardware

- Raspberry Pi Zero W
- Raspberry Pi OS with Desktop (32-bit)
- Seven-inch HDMI touchscreen
- Mini-HDMI-to-HDMI cable
- USB OTG hub
- Keyboard and mouse during development
- Dedicated power supplies for the Pi and display

## Install

Clone the repository on the Raspberry Pi:

```bash
cd ~
git clone https://github.com/trent229/raspberry-pi-touchscreen-ui.git
cd raspberry-pi-touchscreen-ui
chmod +x install.sh
./install.sh
```

Start the interface immediately:

```bash
python3 app.py
```

The installer creates a desktop autostart entry. After installation, the
interface starts automatically whenever the Raspberry Pi desktop session
starts.

## Controls

- Use the navigation bar to open Dashboard, Touch Test, System, and Power.
- Drag a finger on the Touch Test canvas to verify panel accuracy.
- Press `F11` to toggle full-screen mode.
- Press `Escape` to leave full-screen mode during development.
- Restart and shutdown actions require on-screen confirmation.

## Project Purpose

This project demonstrates embedded-computer configuration, HDMI and USB device
integration, touchscreen input, human-machine interface design, live system
monitoring, and automatic application startup.

## License

Released under the MIT License.
