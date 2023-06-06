import torch
from UnarySim.stream import RawScale


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def test_rawscale():
    hwcfg = {
            "width" : 8,
            "mode" : "bipolar",
            "dimr" : 1,
            "rng" : "sobol",
            "scale" : 1,
            "quantile": 0.95
        }
    swcfg = {
            "rtype" : torch.float,
            "stype" : torch.float,
            "btype" : torch.float
        }

    input = torch.randn([256, 256]).to(device)
    print(input)
    srcbin = RawScale(hwcfg).to(device)
    print(srcbin(input))


if __name__ == '__main__':
    test_rawscale()
