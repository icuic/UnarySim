import torch

class FSUAdd(torch.nn.Module):
    """
    This module is for unary addition for arbitrary scale, including scaled/non-scaled, unipolar/bipolar.
    """
    def __init__(
        self, 
        hwcfg={
            "mode" : "bipolar", 
            "scale" : None,
            "dima" : 0,
            "depth" : 10,
            "entry" : None
        }, 
        swcfg={
            "btype" : torch.float, 
            "stype" : torch.float
        }):
        super(FSUAdd, self).__init__()
        self.hwcfg = {}
        self.hwcfg["depth"] = hwcfg["depth"]
        self.hwcfg["mode"] = hwcfg["mode"].lower()
        self.hwcfg["scale"] = hwcfg["scale"]
        self.hwcfg["dima"] = hwcfg["dima"]
        self.hwcfg["entry"] = hwcfg["entry"]

        self.swcfg = {}
        self.swcfg["btype"] = swcfg["btype"]
        self.swcfg["stype"] = swcfg["stype"]

        # data representation
        self.mode = hwcfg["mode"].lower()
        assert self.mode in ["unipolar", "bipolar"], \
            "Error: the hw config 'mode' in " + str(self) + " class requires one of ['unipolar', 'bipolar']."

        # scale is an arbitrary value that larger than 0
        self.scale = hwcfg["scale"]
        # dimension to do reduced sum
        self.dima = hwcfg["dima"]
        # depth of the accumulator
        self.depth = hwcfg["depth"]
        # number of entries in dima to do reduced sum
        self.entry = hwcfg["entry"]

        # max value in the accumulator
        self.acc_max = 2**(self.depth-2)
        # min value in the accumulator
        self.acc_min = -2**(self.depth-2)
        self.stype = swcfg["stype"]
        self.btype = swcfg["btype"]
        
        # the carry scale at the output
        self.scale_carry = torch.nn.Parameter(torch.ones(1), requires_grad=False)
        # accumulation offset
        self.offset = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
        # accumulator for (PC - offset)
        self.accumulator = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
        self.first = True

    def forward(self, input, scale=None, entry=None):
        if self.first:
            if entry is not None:
                # runtime entry will override the default value
                self.entry = entry
                self.hwcfg["entry"] = entry
            else:
                if self.entry is None:
                    self.entry = input.size()[self.dima]
                    self.hwcfg["entry"] = input.size()[self.dima]
                else:
                    self.entry = self.entry
                    self.hwcfg["entry"] = self.entry

            if scale is not None:
                # runtime scale will override the default value
                self.scale_carry.fill_(scale)
                self.hwcfg["scale"] = scale
            else:
                if self.scale is None:
                    self.scale_carry.fill_(self.entry)
                    self.hwcfg["scale"] = self.entry
                else:
                    self.scale_carry.fill_(self.scale)
                    self.hwcfg["scale"] = self.scale

            if self.mode == "bipolar":
                self.offset.data = (self.entry - self.scale_carry)/2
            self.hwcfg["offset"] = self.offset

            self.first = False
        else:
            pass

        acc_delta = torch.sum(input.type(self.btype), self.dima) - self.offset
        self.accumulator.data = self.accumulator.add(acc_delta).clamp(self.acc_min, self.acc_max)
        output = torch.ge(self.accumulator, self.scale_carry).type(self.btype)
        self.accumulator.sub_(output * self.scale_carry).clamp_(self.acc_min, self.acc_max)
        return output.type(self.stype)

