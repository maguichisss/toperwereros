

psql -d nombre_base_datos -U nombre_usuario

\dt
select * from products;
delete from categories where id>20;
delete from categories where name='Clothing';
UPDATE colors SET name = 'violeta/morado' WHERE id=74;




select name, code, stock, price, ubicacion from products;

select name, code, stock, price, ubicacion from products where ubicacion like '%Caja 1';
select name, code, stock, price, ubicacion from products where ubicacion like '%caja 1';
select name, code, stock, price, ubicacion from products where ubicacion like '%caja1%';
select name, code, stock, price, ubicacion from products where ubicacion like 'estante blanco%';

update products set ubicacion = 'Caja 01' where ubicacion='Caja1';
update products set ubicacion = 'Caja 01' where ubicacion='caja1';
update products set ubicacion = 'Caja 01' where ubicacion='Caja 1';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 3';
select name, code, stock, price, ubicacion from products where ubicacion='Caja3';
update products set ubicacion = 'Caja 03' where ubicacion='Caja3';
update products set ubicacion = 'Caja 03' where ubicacion='Caja 3';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 2';
update products set ubicacion = 'Caja 02' where ubicacion='Caja 2';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 02';

select name, code, stock, price, ubicacion from products where ubicacion='10';
update products set ubicacion = 'Caja 10' where ubicacion='10';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 10';

select name, code, stock, price, ubicacion from products where ubicacion='13';
update products set ubicacion = 'Caja 13' where ubicacion='13';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 13';

select name, code, stock, price, ubicacion from products where ubicacion='Estante1';
update products set ubicacion = 'Estante 1' where ubicacion='Estante1';
select name, code, stock, price, ubicacion from products where ubicacion='Estante 1';

select name, code, stock, price, ubicacion from products where ubicacion='Caja7';
update products set ubicacion = 'Caja 7' where ubicacion='Caja7';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 7';


update products set ubicacion = 'Caja 01' where ubicacion='Caja 1';
update products set ubicacion = 'Caja 9' where ubicacion='Caja  9';
update products set ubicacion = 'Estante blanco' where ubicacion='estante blanco';


select ubicacion, sum(stock*price) from products group by ubicacion;
