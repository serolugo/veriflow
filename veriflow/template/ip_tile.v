`timescale 1ns / 1ps

module ip_tile #(
parameter REG_WIDTH     = 32,
parameter CSR_IN_WIDTH  = 16,
parameter CSR_OUT_WIDTH = 16)
(
input  wire                      clk,
input  wire                      arst_n,
input  wire [CSR_IN_WIDTH-1:0]   csr_in,
input  wire [REG_WIDTH-1:0]      data_reg_a,
input  wire [REG_WIDTH-1:0]      data_reg_b,
output wire [REG_WIDTH-1:0]      data_reg_c,
output wire [CSR_OUT_WIDTH-1:0]  csr_out,
output wire                      csr_in_re,
output wire                      csr_out_we
);

  // USER LOGIC STARTS HERE //

  // USER LOGIC ENDS HERE //

endmodule
