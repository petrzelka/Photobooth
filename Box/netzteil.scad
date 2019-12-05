w = 70;
l = 100;
t = 36;

difference() {
    cube([w+4, l, t+4]);
    translate([2, -2, 2]) cube([w, l, t]);
    translate([w/2+2, l/2-2, 5]) cube([w/2, l, t], center=true);
    translate([5, 2, 2]) cube([w*1/3, l, t-5]);
    translate([w*1/3-4, 2, -5]) cube([9, l, t-5]);
}

translate([-15, 0, t-1]) a();
translate([w+15+4, 0, t-1]) mirror([1,0,0]) a();
translate([-15, l, t-1]) mirror([0,1,0]) a();
translate([w+15+4, l, t-1]) rotate([0,0,180]) a();


module a() {
    difference() {
        cube([15, 30, 5]);
        translate([7.5, 7.5, 2.9]){ 
            rotate([0,180,0]) cylinder(d1=0, d2=6, h=3, $fn=20);
        }
        translate([7.5, 7.5, 0]){ 
            cylinder(d=3.5, h=10, $fn=20);
        }
        translate([0,15,-1])
            rotate([0,0,45])
                cube([30, 30, 30]);
    }
}