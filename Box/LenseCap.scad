d1 = 23;
d_lens = 7;
h = 2;

difference() {
    union() {
        cylinder(d=d1, h=3*h, $fn=100);
    }
    translate([0,0,1]) cylinder(d=d1-4, h=h+10, $fn=100);    
    translate([0,0,-5]) cylinder(d=d_lens, h=h+10, $fn=100);    
}