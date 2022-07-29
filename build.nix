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
  name = "europe-west2-docker.pkg.dev/titled-jam-team/titled-jam-team/cloud-build-webhook";
  tag = (builtins.getEnv "sha");
  contents = [ app.dependencyEnv ];
  config.Cmd = [ "/bin/python3" "-m" "cloud-build-webhook" ];
}
