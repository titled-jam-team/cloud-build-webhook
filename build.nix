{ pkgs ? import <nixpkgs> { }
, pkgsLinux ? import <nixpkgs> { system = "x86_64-linux"; }
}:

# I copied this code off the Internet.
# I don't know what it does.
# bs2k please help me

let
  pkgs = import <nixpkgs> {};
  app = pkgs.poetry2nix.mkPoetryApplication {
    projectDir = ./.;
  };
in pkgs.dockerTools.streamLayeredImage {
  name = "predictable";
  contents = [ app.dependencyEnv ./src ];
  config.Cmd = [ "/bin/python3" "main.py" ];
}
