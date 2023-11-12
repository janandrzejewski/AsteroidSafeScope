# AsteroidSafeScope
Protecting Observations from Stellar Interference 

AsteroidSafeScope is a tool designed for swift verification during asteroid observation planning. It aids in quickly checking if stars are present along the path of an asteroid, facilitating efficient observation planning.
![image](https://github.com/janandrzejewski/AsteroidSafeScope/assets/67760124/d9f0de39-cc3e-4d62-aa2c-8f6242eb404d)

## Requirements
- Python 3.8+

## Usage

To utilize AsteroidSafeScope:
- Provide the asteroid names or their IDs, separated by commas, for analysis.
- Select the observation date using the calendar feature.
- Confirm the selection to initiate the verification process.

## Installation (Development)

# For development usage:

Create a new Conda environment:
```commandline
conda create --name asteroid_env --file requirements.txt
```
Activate the Conda environment:
```commandline
conda activate asteroid_env
```
Run the programs:

- Execute the asteroid data processing script:

```commandline
python asteroid_data_processing.py
```
- Launch the asteroid visualization script:

```commandline
python asteroid_visualization.py
```

## Development

Imports are organized with `isort`.

Code is formatted with `black`.

![Carina_altitude_20231112](https://github.com/janandrzejewski/AsteroidSafeScope/assets/67760124/35d31300-5785-4ca7-af6a-e137ce68eed3)
![Carina_stars_20231112](https://github.com/janandrzejewski/AsteroidSafeScope/assets/67760124/8a637a15-af5e-4371-8cd1-5c843dc19ab4)

