`include "../jkff/JKFF.sv"
`include "../../stream/shuffle/Bi2Uni.sv"

module BISQRT_S_JK_B # (
    parameter DEP=3
) (
    input logic clk,    // Clock
    input logic rst_n,  // Asynchronous reset active low
    input logic in,
    output logic out
);
    
    logic [1:0] mux;
    logic sel;
    logic trace;

    logic Jport;
    logic Kport;
    logic JKout;
    logic outUni;
    
    assign mux[0] = in;
    assign mux[1] = 1;
    assign out = sel ? mux[1] : mux[0];
    assign sel = trace;

    assign trace = JKout;
    assign Jport = outUni;
    assign Kport = 1;

    JKFF U_JKFF(
        .clk(clk),
        .rst_n(rst_n),
        .J(Jport),
        .K(Kport),
        .out(JKout)
        );

    Bi2Uni #(
        .DEP(DEP)
    ) U_Bi2Uni(
        .clk(clk),
        .rst_n(rst_n),
        .in(in),
        .out(outUni)
        );

endmodule
