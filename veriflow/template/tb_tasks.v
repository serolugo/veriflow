task write_data_reg_a(input [31:0] data);
    begin
        @(posedge clk);
        data_reg_a = data;
    end
endtask

task write_data_reg_b(input [31:0] data);
    begin
        @(posedge clk);
        data_reg_b = data;
    end
endtask

task write_csr_in(input [15:0] data);
    begin
        csr_in = data;
        @(posedge clk);
    end
endtask

task reset_csr_in;
    begin
        csr_in[15:12] = 4'b0;
    end
endtask

task read_csr_out(output [15:0] data);
    begin
        data = csr_out;
        @(posedge clk);
    end
endtask
