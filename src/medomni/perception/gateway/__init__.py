"""Service API gateway over the encoder container pool (R-25): catalogue, evidence, router.

catalog: cards from disk, no docker.  pool: slot state machine, no HTTP.  runner: the one Docker runner, the only
module that shells out.  app: routes, no logic.  config: the workspace's deployment.
"""
