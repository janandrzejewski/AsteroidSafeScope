# AsteroidSafeScope
Protecting Observations from Stellar Interference 

AsteroidSafeScope is a tool designed for swift verification during asteroid observation planning. It aids in quickly checking if stars are present along the path of an asteroid, facilitating efficient observation planning.

![example usage](image-2.png)

## Requirements
- Python 3.10+
- Docker

## Usage

To utilize AsteroidSafeScope:
- Enter the longitude, latitude, and altitude of the observation location.
- Provide the asteroid names or their IDs, separated by commas, for analysis.
- Select the observation date using the calendar feature.
- Confirm the selection to initiate the verification process.

![config program](image.png)
## Installation (Development)

### For development usage:

Download code:
```commandline
git clone https://github.com/janandrzejewski/AsteroidSafeScope
```
install docker and compose plugin
- https://docs.docker.com/engine/install/
- https://docs.docker.com/compose/install/linux/#install-the-plugin-manually

Run the server:

```commandline
sudo docker compose up -d --build
```

## Development

Imports are organized with `isort`.

Code is formatted with `black`.

![Carina_altitude_20231112](https://github.com/janandrzejewski/AsteroidSafeScope/assets/67760124/35d31300-5785-4ca7-af6a-e137ce68eed3)
![Carina_stars_20231112](https://github.com/janandrzejewski/AsteroidSafeScope/assets/67760124/8a637a15-af5e-4371-8cd1-5c843dc19ab4)

