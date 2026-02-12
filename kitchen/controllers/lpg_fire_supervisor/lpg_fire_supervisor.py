"""Minimal LPG fire supervisor controller for Webots kitchen world."""
from controller import Supervisor

TIME_STEP = 32
supervisor = Supervisor()

while supervisor.step(TIME_STEP) != -1:
    # Supervisor runs; add fire/safety logic here if needed
    pass
