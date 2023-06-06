import torch
from UnarySim.kernel import FSUDiv
from UnarySim.stream import RNG, BinGen, BSGen
from UnarySim.metric import ProgError
import matplotlib.pyplot as plt

from matplotlib import ticker, cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import time
import math
import numpy as np


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def test_fsudiv():
    hwcfg = {
            "width" : 8,
            "mode" : "unipolar",
            "rng" : "Sobol",
            "dimr" : 4,
            "scale" : 1,
            "depth_sa" : 3,
            "depth_ss" : 2,
            "entry_kn" : 2
        }
    swcfg = {
            "rtype" : torch.float,
            "stype" : torch.float,
            "btype" : torch.float
        }

    bitwidth=hwcfg["width"]
    mode=hwcfg["mode"]
    total_cnt=1
    savepdf=False
    stype = swcfg["stype"]
    btype = swcfg["btype"]
    rtype = swcfg["rtype"]

    print("========================================================")
    print(mode)
    print("========================================================")
    if mode == "unipolar":
        # all values in unipolar are non-negative
        # dividend is always non greater than divisor
        # divisor is non-zero
        low_bound = 0
        up_bound = 2**bitwidth
    elif mode == "bipolar":
        # values in bipolar are arbitrarily positive or negative
        # abs of dividend is always non greater than abs of divisor
        # abs of divisor is non-zero
        low_bound = -2**(bitwidth-1)
        up_bound = 2**(bitwidth-1)

    divisor_list = []
    dividend_list = []
    for divisor_val in range(up_bound, low_bound-1, -1):
        divisor_list.append([])
        dividend_list.append([])
        for dividend_val in range(low_bound, up_bound+1, 1):
            divisor_list[up_bound-divisor_val].append(divisor_val)
            dividend_list[up_bound-divisor_val].append(dividend_val)
    
    dividend = torch.tensor(dividend_list).type(torch.float).div(up_bound).to(device)
    divisor = torch.tensor(divisor_list).type(torch.float).div(up_bound).to(device)
    quotient = dividend.div(divisor)
    
    # find the invalid postions in quotient
    quotient_nan = torch.isnan(quotient)
    quotient_inf = torch.isinf(quotient)
    quotient_mask = quotient_nan + quotient_inf
    quotient[quotient_mask] = 0
    quotient = quotient.clamp(-1, 1)
    
    result_pe_total = []
    for rand_idx in range(1, total_cnt+1):
        quotientPE = ProgError(quotient, hwcfg).to(device)
    
        dividendPE = ProgError(dividend, hwcfg).to(device)
        dividendSRC = BinGen(dividend, hwcfg, swcfg)().to(device)

        divisorPE  = ProgError(divisor, hwcfg).to(device)
        divisorSRC = BinGen(divisor, hwcfg, swcfg)().to(device)
    
        dut_div = FSUDiv(hwcfg, swcfg).to(device)

        hwcfg["dimr"] = 1
        dividendRNG = RNG(hwcfg, swcfg)().to(device)
        dividendBS = BSGen(dividendSRC, dividendRNG, swcfg).to(device)
        divisorRNG = RNG(hwcfg, swcfg)().to(device)
        divisorBS = BSGen(divisorSRC, divisorRNG, swcfg).to(device)
        with torch.no_grad():
            start_time = time.time()
            for i in range(2**bitwidth):
                dividend_bs = dividendBS(torch.tensor([i]))
                dividendPE.Monitor(dividend_bs)

                divisor_bs = divisorBS(torch.tensor([i]))
                divisorPE.Monitor(divisor_bs)

                quotient_bs = dut_div(dividend_bs, divisor_bs)   
                quotientPE.Monitor(quotient_bs)
        
        # get the result for different rng
        result_pe = quotientPE()[1].cpu().numpy()
        result_pe[quotient_mask.cpu().numpy()] = np.nan
        result_pe_total.append(result_pe)
    
    # get the result for different rng
    result_pe_total = np.array(result_pe_total)
    
    #######################################################################
    # check the error of all simulation
    #######################################################################
    result_pe_total_no_nan = result_pe_total[~np.isnan(result_pe_total)]
    print("RMSE:{:1.4}".format(math.sqrt(np.mean(result_pe_total_no_nan**2))))
    print("MAE: {:1.4}".format(np.mean(np.abs(result_pe_total_no_nan))))
    print("bias:{:1.4}".format(np.mean(result_pe_total_no_nan)))
    print("max: {:1.4}".format(np.max(result_pe_total_no_nan)))
    print("min: {:1.4}".format(np.min(result_pe_total_no_nan)))

    # #######################################################################
    # # check the error according to input value
    # #######################################################################
    # avg_total = np.mean(result_pe_total, axis=0)
    # avg_total[quotient_mask.cpu().numpy()] = 0
    # fig, ax = plt.subplots()
    # fig.set_size_inches(5.5, 4)
    # axis_len = quotientPE()[1].size()[0]
    # divisor_y_axis = []
    # dividend_x_axis = []
    # for axis_index in range(axis_len):
    #     divisor_y_axis.append((up_bound-axis_index/(axis_len-1)*(up_bound-low_bound))/up_bound)
    #     dividend_x_axis.append((axis_index/(axis_len-1)*(up_bound-low_bound)+low_bound)/up_bound)
    # X, Y = np.meshgrid(dividend_x_axis, divisor_y_axis)
    # Z = avg_total
    # levels = [-0.09, -0.06, -0.03, 0.00, 0.03, 0.06, 0.09]
    # cs = plt.contourf(X, Y, Z, levels, cmap=cm.RdBu, extend="both")
    # cbar = fig.colorbar(cs)
    
    # # plt.tight_layout()
    # plt.xticks(np.arange(low_bound/up_bound, up_bound/up_bound+0.1, step=0.5))
    # # ax.xaxis.set_ticklabels([])
    # plt.yticks(np.arange(low_bound/up_bound, up_bound/up_bound+0.1, step=0.5))
    # # ax.yaxis.set_ticklabels([])
    
    # if savepdf is True:
    #     plt.savefig("div-"+mode+"-bw"+str(bitwidth)+"-k"+str(depth_kernel)+"-ISCB"+".pdf", 
    #                 dpi=300, 
    #                 bbox_inches='tight')
                
    # plt.show()
    # plt.close()


if __name__ == '__main__':
    test_fsudiv()
