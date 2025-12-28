"""
乘法群模块 - 定义和实现素数阶循环群
"""

from sympy import isprime

class PrimeOrderCyclicGroup:
    def __init__(self, p: int, g: int):
        """
        初始化素数阶循环群
        
        Args:
            p: 素数 p
            g: 生成元 g
        """
        self.p = p
        self.g = g

    def extended_gcd(self, a, b):
        """
        扩展欧几里得算法，返回 a 和 b 的最大公约数以及系数 x 和 y，
        使得 a * x + b * y = gcd(a, b)
        
        Args:
            a: 整数a
            b: 整数b
            
        Returns:
            元组 (gcd, x, y)，其中 gcd 是 a 和 b 的最大公约数，x 和 y 满足 ax + by = gcd
        """
        if b == 0:
            return a, 1, 0
        else:
            gcd, x1, y1 = self.extended_gcd(b, a % b)
            x = y1
            y = x1 - (a // b) * y1
            return gcd, x, y

    def mod_inverse(self, a):
        """
        计算元素 a 在模 p 下的逆元
        
        Args:
            a: 要求逆元的元素
            
        Returns:
            a在模p下的逆元
            
        Raises:
            ValueError: 如果a和p不互质，无法求逆元
        """
        gcd, x, y = self.extended_gcd(a, self.p)
        if gcd != 1:
            raise ValueError(f"{a} 和 {self.p} 不是互质的，无法求逆元")
        else:
            return x % self.p  # 确保逆元在 [0, p-1] 范围内

    def check_inverse(self, a, a_inv):
        """
        检查给定元素 a 和其逆元 a_inv 是否满足 a * a_inv ≡ 1 (mod p)
        
        Args:
            a: 元素
            a_inv: 元素的逆元
            
        Returns:
            布尔值，表示是否满足逆元条件
        """
        return (a * a_inv) % self.p == 1

# 如果直接运行此文件，将执行简单的测试
if __name__ == "__main__":
    p = 32256122104168516640186411076711910158316130087780330483927893781692175210003921834144834215262833140777092329970719  # 示例素数 p
    g = 11622542012320274819566989409473007590240355952069251148223774837288904382080522629621759436605312646725259323821617   # 示例生成元 g
    
    group = PrimeOrderCyclicGroup(p, g)

    # 假设我们要计算元素 5 的逆元
    a = 5
    inverse_a = group.mod_inverse(a)
    print(f"在 Z_{p}* 中，元素 {a} 的逆元是: {inverse_a}")

    # 检查逆元是否正确
    if group.check_inverse(a, inverse_a):
        print(f"逆元验证成功：{a} * {inverse_a} ≡ 1 (mod {p})")
    else:
        print(f"逆元验证失败：{a} * {inverse_a} ≡ 1 (mod {p})")
