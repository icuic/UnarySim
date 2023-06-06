`include "../div/CORDIV_kernel.sv"

module BISQRT_S_IS_U #(
    parameter DEP=1,
    parameter DEPLOG=1
) (
    input logic clk,    // Clock
    input logic rst_n,  // Asynchronous reset active low
    input logic [DEPLOG-1:0] randNum,
    input logic in,
    output logic out
);
    
    logic [1:0] mux;
    logic sel;
    logic trace;

    logic dividend;
    logic divisor;
    logic quotient;

    logic dff;
    logic dff_inv;

    assign dff_inv = ~dff;

    always_ff @(posedge clk or negedge rst_n) begin : proc_dff
        if(~rst_n) begin
            dff <= 0;
        end else begin
            dff <= dff_inv;
        end
    end

    assign mux[0] = in;
    assign mux[1] = 1;
    always_ff @(posedge clk or negedge rst_n) begin : proc_out
        if(~rst_n) begin
            out <= 0;
        end else begin
            out <= sel ? mux[1] : mux[0];
        end
    end
    assign sel = trace;

    assign trace = quotient;
    assign dividend = dff_inv & out;
    assign divisor = dff | dividend;

    CORDIV_kernel #(
        .DEP(DEP),
        .DEPLOG(DEPLOG)
    ) U_CORDIV_kernel(
        .clk(clk),
        .rst_n(rst_n),
        .randNum(randNum),
        .dividend(dividend),
        .divisor(divisor),
        .quotient(quotient)
    );

endmodule
