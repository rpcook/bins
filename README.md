# Bin Collection Reminder
North Herts Council have made bin collection very complex in mid 2025. Already I have been putting out some form of recycling collection in my dressing gown early one morning, having forgotten to do so the night before.

This project aims to eliminate this in a intiutive manner.

## Genesis
As with most projects, this starts with my wife seeing something on The Socials and asking me if I can make that.

## Overview
Web scraper to determine next collection hosted on a Raspberry Pi. On the day before, flash an LED (of relevant colour). Basic control via push button to dismiss reminder etc.

# Project Burndown
## Minimum Viable Product
- ~~Design schematic~~
- ~~Design RPi Hat layout~~
- ~~Build Hat~~
- ~~Configure RPi Zero~~
- ~~Build prototype~~
- ~~Test prototype basic functionality~~
- ~~Write button handler (single, double, long-press)~~
- ~~Test PWM LED control~~
  - ~~Capture relevant colour codes~~
- ~~Write web scraper~~
- ~~Write web parser~~
- ~~Design software architecture~~
- ~~Implement basic functionality~~

## Complete build
- Build base
  - Brass button
  - UV resin status LED window
- Install electronics
- ~~Build bin model~~
- Install bin model
- ~~Error handling~~
- Support corner case of same bin-day
- ~~Robust watchdog etc~~
  - ~~Soft-reset function~~
- ~~Catch maintenance mode on website~~
- Logging
  - Management of log size
- ~~Rainbow POST for bin~~
- ~~Different user inputs~~

## Someone beat me to it:
~~## Open Source Project (HACS Waste Collection)~~
- ~~Modify scraper to run in HACS installation~~
- ~~Test~~
- ~~Submit pull-request to HACS Waste Collection project~~
