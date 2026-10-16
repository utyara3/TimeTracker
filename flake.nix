{
  description = "Flake description";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python314.withPackages (
          ps: with ps; [
            # Add any packages you need here
            aiogram
            aiosqlite
            python-dotenv
            pandas
          ]
        );
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.ruff
          ];
        };

        shellHook = ''
          echo "Nix Python environment ready"
          python --version
        '';
      }
    );
}
