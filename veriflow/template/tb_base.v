`timescale 1ns / 1ps

module tb;

parameter CSR_IN_WIDTH  = 16;
parameter CSR_OUT_WIDTH = 16;
parameter REG_WIDTH     = 32;

reg clk;
reg arst_n;
reg  [CSR_IN_WIDTH-1:0]  csr_in;
reg  [REG_WIDTH-1:0]     data_reg_a;
reg  [REG_WIDTH-1:0]     data_reg_b;
wire [REG_WIDTH-1:0]     data_reg_c;
wire [CSR_OUT_WIDTH-1:0] csr_out;
wire                     csr_in_re;
wire                     csr_out_we;

`include "tb_tasks.v"

always #5 clk = ~clk;

/* MODULE_INSTANTIATION */

initial begin
    $dumpfile("waves.vcd");
    $dumpvars(0, tb);
end

initial begin
    clk        = 0;
    arst_n     = 0;
    csr_in     = 0;
    data_reg_a = 0;
    data_reg_b = 0;
    repeat(2) @(posedge clk);
    arst_n = 1;
    repeat(1) @(posedge clk);

    // USER TEST STARTS HERE //

    // USER TEST ENDS HERE //

    $finish;
end

endmodule
